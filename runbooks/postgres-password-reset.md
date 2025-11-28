# Resetting PostgreSQL Password in a Kubernetes Pod

Follow these steps to reset the PostgreSQL password when running in a Kubernetes environment:

**1. Access the PostgreSQL pod**

Execute into the running PostgreSQL pod using kubectl.

**2. Locate the authentication configuration**

Navigate to `/opt/bitnami/postgresql/conf/` and open the `pg_hba.conf` file. The default configuration typically looks like this:

```
host     all             all             0.0.0.0/0               md5
host     all             all             ::/0                    md5
local    all             all                                     md5
host     all             all        127.0.0.1/32                 md5
host     all             all        ::1/128                      md5
```

**3. Temporarily disable authentication**

Modify `pg_hba.conf` to allow connections without password verification by changing `md5` to `trust`:

```
host     all             all             0.0.0.0/0               trust
host     all             all             ::/0                    trust
local    all             all                                     trust
host     all             all        127.0.0.1/32                 trust
host     all             all        ::1/128                      trust
```

Save your changes.

**4. Apply the configuration**

Reload PostgreSQL to use the updated configuration:

```bash
pg_ctl reload
```

**5. Reset the password**

Change the password using psql:

```bash
psql -U postgres -c "ALTER USER postgres PASSWORD 'newpassword';"
```

**6. Restore secure authentication**

Revert `pg_hba.conf` back to `md5` authentication to restore security. Save the file.

**7. Finalize the changes**

Reload PostgreSQL one final time:

```bash
pg_ctl reload
```

Your PostgreSQL password has now been successfully reset with authentication security restored.
