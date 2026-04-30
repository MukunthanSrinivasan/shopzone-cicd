terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_vpc" "shopzone_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = { Name = "shopzone-vpc" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.shopzone_vpc.id
  tags   = { Name = "shopzone-igw" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.shopzone_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true
  tags = { Name = "shopzone-subnet" }
}

resource "aws_route_table" "rt" {
  vpc_id = aws_vpc.shopzone_vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
}

resource "aws_route_table_association" "rta" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.rt.id
}

resource "aws_security_group" "shopzone_sg" {
  name   = "shopzone-sg"
  vpc_id = aws_vpc.shopzone_vpc.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "shopzone-sg" }
}

resource "aws_instance" "shopzone_server" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t3.micro"
  key_name               = "shopzone-key"
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.shopzone_sg.id]

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  user_data = <<-EOF
    #!/bin/bash
    apt-get update -y
    apt-get install -y python3-pip python3-venv git curl
    mkdir -p /data
  EOF

  tags = { Name = "shopzone-app-server" }
}

output "instance_public_ip" {
  value = aws_instance.shopzone_server.public_ip
}

output "application_url" {
  value = "http://${aws_instance.shopzone_server.public_ip}:5000"
}
