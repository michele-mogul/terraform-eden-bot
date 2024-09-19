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

data "archive_file" "zip_the_python_code" {

  type        = "zip"
  source_dir  = "${path.module}/../src/"
  output_path = "${path.module}/build/eden.zip"

}

resource "aws_lambda_function" "terraform_lambda_func" {

  filename         = "${path.module}/build/eden.zip"
  function_name    = "EdenBotLambdaFunction"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.lambda_handler"
  runtime          = "python3.8"
  source_code_hash = data.archive_file.zip_the_python_code.output_base64sha256
  depends_on       = [aws_iam_role_policy_attachment.attach_iam_policy_to_iam_role]
  environment {
    variables = {
      telegram_key = var.telegram_key
    }
  }
}


resource "aws_lambda_function_url" "test_live" {
  function_name      = aws_lambda_function.terraform_lambda_func.function_name
  authorization_type = "NONE"
}

resource "null_resource" "docker_build" {

  triggers = {
    always_run = timestamp()
  }

  provisioner "local-exec" {
    command = "python ${path.module}/setup-webhook.py -w ${aws_lambda_function_url.test_live.function_url} -t ${var.telegram_key}"
  }
}