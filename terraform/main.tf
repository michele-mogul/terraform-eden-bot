provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

resource "aws_iam_role" "lambda_role" {
  name               = "Eden_Bot_Lambda_Function_Role"
  assume_role_policy = <<EOF
{
 "Version": "2012-10-17",
 "Statement": [
   {
     "Action": "sts:AssumeRole",
     "Principal": {
       "Service": "lambda.amazonaws.com"
     },
     "Effect": "Allow",
     "Sid": ""
   }
 ]
}
EOF
}

resource "aws_iam_policy" "iam_policy_for_lambda" {

  name        = "aws_iam_policy_for_terraform_aws_lambda_role"
  path        = "/"
  description = "AWS IAM Policy for managing aws lambda role"
  policy      = <<EOF

{
 "Version": "2012-10-17",
 "Statement": [
   {
     "Action": [
       "logs:CreateLogGroup",
       "logs:CreateLogStream",
       "logs:PutLogEvents"
     ],
     "Resource": "arn:aws:logs:*:*:*",
     "Effect": "Allow"
   }
 ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "attach_iam_policy_to_iam_role" {

  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.iam_policy_for_lambda.arn

}

resource "null_resource" "layer_generation" {
  provisioner "local-exec" {
    command = "pip install --platform=manylinux_2_17_x86_64 --only-binary=:all: -r ${path.module}/../src/requirements.txt -t ${path.module}/build/layer/python/"
  }
}

data "archive_file" "zip_the_python_code" {
  type        = "zip"
  source_dir  = "${path.module}/../src/"
  output_path = "${path.module}/build/eden.zip"
  excludes    = [".venv"]
}

data "archive_file" "zip_dependencies_layer" {
  type        = "zip"
  source_dir  = "${path.module}/build/layer"
  output_path = "${path.module}/build/layer.zip"
  depends_on = [null_resource.layer_generation]
}

resource "aws_lambda_layer_version" "layer" {
  layer_name = "lambda_layer"
  filename = "${path.module}/build/layer.zip"
  compatible_architectures = ["x86_64"]
  compatible_runtimes = ["python3.12"]
  source_code_hash = data.archive_file.zip_dependencies_layer.output_base64sha256
}

resource "aws_lambda_function" "terraform_lambda_func" {

  filename      = "${path.module}/build/eden.zip"
  function_name = "EdenBotLambdaFunction"
  role          = aws_iam_role.lambda_role.arn
  handler       = "index.lambda_handler"
  runtime       = "python3.12"
  depends_on    = [aws_iam_role_policy_attachment.attach_iam_policy_to_iam_role]
  environment {
    variables = {
      telegram_key = var.telegram_key
    }
  }

  layers = [
    aws_lambda_layer_version.layer.arn,
  ]
  source_code_hash = data.archive_file.zip_the_python_code.output_base64sha256
}

resource "aws_lambda_permission" "allow_url_invoke" {
  statement_id  = "AllowPublicInvoke"
  action        = "lambda:InvokeFunctionUrl"
  function_name = aws_lambda_function.terraform_lambda_func.arn
  function_url_auth_type = "NONE"
  principal     = "*"
}


resource "aws_lambda_function_url" "test_live" {
  function_name      = aws_lambda_function.terraform_lambda_func.arn
  authorization_type = "NONE"
}

output "lambda_invoke_url" {
  sensitive = true
  value     = "https://api.telegram.org/bot${var.telegram_key}/setWebhook?url=${aws_lambda_function_url.test_live.function_url}&drop_pending_updates=true&allowed_updates=${jsonencode(["callback_query","message"])}"
}