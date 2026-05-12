# Terraform — Hetzner CX22 provisioning

Provisions a single Hetzner CX22 server in `fsn1` (Falkenstein) with firewall (22/80/443) and SSH key.

## Setup

1. Create a Hetzner Cloud project at https://console.hetzner.cloud/
2. Generate API token (Security → API Tokens, Read & Write)
3. Copy `terraform.tfvars.example` to `terraform.tfvars` (not committed):
   ```hcl
   hcloud_token   = "your-token-here"
   ssh_public_key = "ssh-ed25519 AAAAC3... your@host"
   ```

## Commands

```bash
terraform init
terraform plan
terraform apply       # asks for confirmation
terraform output server_ip
```

## Destroy

```bash
terraform destroy
```

TODO: remote state backend (S3-compatible / Terraform Cloud).
