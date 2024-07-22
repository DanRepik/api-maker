# Set the database name (optional)
#pulumi config set dbName mydb

# Set the database username (optional)
pulumi config set dbUsername chinook_user

# Set the database password (required, secret value)
pulumi config set --secret dbPassword chinook_password

# Set the database instance class (optional)
pulumi config set dbInstanceClass db.t3.micro

# Set the allocated storage (optional)
pulumi config set dbAllocatedStorage 20

# Set the backup retention period (optional)
pulumi config set dbBackupRetention 7
