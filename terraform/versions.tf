terraform {
  required_version = ">= 1.5"

  backend "s3" {
    bucket         = "einstein-test-tfstate-prod"
    key            = "einstein-test/prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "einstein-test-tfstate-locks-prod"
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}