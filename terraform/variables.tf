variable "aws_region" {
  type        = string
  description = "AWS Region for deploy"
}

variable "aws_profile" {
  type        = string
  description = "AWS Profile for deploy"
}

variable "telegram_key" {
  type        = string
  sensitive   = true
  description = "Telegram bot default key"
}
