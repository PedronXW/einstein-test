# ---------------------------------------------------------------------------
# GitHub Actions (OIDC) — roles de deploy. Moram aqui (bootstrap) para o CI
# poder assumi-las desde o 1º apply (o backend/state também é criado aqui).
# ---------------------------------------------------------------------------

data "aws_caller_identity" "current" {}

locals {
  name = "${var.project}-${var.environment}"
}

resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "a031c6f5c7b556ffd07e14b56ec4dc8fed121de2",
  ]
}

data "aws_iam_policy_document" "github_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:ref:refs/heads/main"]
    }
  }
}

# Role do job de INFRA no CI (terraform plan/apply) — escopo amplo por
# provisionar todos os recursos do stack. Reduza as políticas anexadas se
# preferir least-privilege.
locals {
  github_infra_policies = [
    "arn:aws:iam::aws:policy/AmazonEC2FullAccess",
    "arn:aws:iam::aws:policy/AmazonVPCFullAccess",
    "arn:aws:iam::aws:policy/AmazonECS_FullAccess",
    "arn:aws:iam::aws:policy/AmazonRDSFullAccess",
    "arn:aws:iam::aws:policy/AmazonElastiCacheFullAccess",
    "arn:aws:iam::aws:policy/AmazonS3FullAccess",
    "arn:aws:iam::aws:policy/SecretsManagerReadWrite",
    "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
    "arn:aws:iam::aws:policy/IAMFullAccess",
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess",
  ]
}

resource "aws_iam_role" "github_infra" {
  name               = "${local.name}-github-infra"
  assume_role_policy = data.aws_iam_policy_document.github_assume.json
  managed_policy_arns = concat(
    local.github_infra_policies,
    [aws_iam_policy.github_infra_elb.arn],
  )

  tags = { Name = "${local.name}-github-infra" }
}

# A AWS removeu as policies gerenciadas AmazonElasticLoadBalancing*
# (não existem mais para attach) — cobrimos o ALB/TG/listener com policy
# própria na role de infra.
data "aws_iam_policy_document" "github_infra_elb" {
  statement {
    sid       = "ElasticLoadBalancingFull"
    actions   = ["elasticloadbalancing:*"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "github_infra_elb" {
  name   = "${local.name}-github-infra-elb"
  policy = data.aws_iam_policy_document.github_infra_elb.json
}

# Role do job de APP no CI (push ECR + rollout ECS) — escopo mínimo.
data "aws_iam_policy_document" "github_app" {
  statement {
    sid       = "ECRGetAuthToken"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid = "ECRPushPull"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:GetRepositoryPolicy",
      "ecr:DescribeRepositories",
      "ecr:ListImages",
      "ecr:DescribeImages",
      "ecr:BatchGetImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:PutImage",
    ]
    resources = ["*"]
  }

  statement {
    sid = "ECSDeploy"
    actions = [
      "ecs:RegisterTaskDefinition",
      "ecs:DescribeTaskDefinition",
      "ecs:UpdateService",
      "ecs:DescribeServices",
      "ecs:DescribeClusters",
      "ecs:ListServices",
    ]
    resources = ["*"]
  }

  # As task/execution roles são criadas pelo terraform principal, mas com nomes
  # determinísticos — permitir PassRole com esses ARNs para o rollout.
  statement {
    sid     = "PassTaskRoles"
    actions = ["iam:PassRole"]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.name}-ecs-execution",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.name}-ecs-task",
    ]
  }
}

resource "aws_iam_policy" "github_app" {
  name   = "${local.name}-github-app"
  policy = data.aws_iam_policy_document.github_app.json
}

resource "aws_iam_role" "github_app" {
  name               = "${local.name}-github-app"
  assume_role_policy = data.aws_iam_policy_document.github_assume.json

  tags = { Name = "${local.name}-github-app" }
}

resource "aws_iam_role_policy_attachment" "github_app" {
  role       = aws_iam_role.github_app.name
  policy_arn = aws_iam_policy.github_app.arn
}

output "github_role_infra_arn" {
  value = aws_iam_role.github_infra.arn
}

output "github_role_app_arn" {
  value = aws_iam_role.github_app.arn
}