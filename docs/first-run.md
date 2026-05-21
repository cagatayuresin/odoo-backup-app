# First Run

## Default Credentials

On first start, the application creates a default admin account:

- **Username:** `admin`
- **Password:** `admin`

## Step 1: Change Your Password

Logging in with `admin`/`admin` immediately redirects you to the **Change Password** screen. You cannot skip this step. Choose a strong password (at least 8 characters).

## Step 2: Configure Timezone

Navigate to **Settings**. Change the timezone from UTC to your local timezone. All cron schedule previews in the UI will use this timezone.

## Step 3: Configure Password Recovery (Strongly Recommended)

Without password recovery, losing your password means permanent loss of access (and inability to decrypt stored secrets).

1. Create an SMTP channel in **Channels → SMTP**
2. Return to **Settings** and:
   - Enable "Password reset via email"
   - Enter your recovery email address
   - Select the SMTP channel you just created

## Step 4: Add Your First Odoo Instance

1. Go to **Instances → Add Instance**
2. Enter the instance name and URL (e.g., `https://erp.mycompany.com`)
3. Choose a backup method:
   - **Odoo Endpoint** — enter the Odoo master password
   - **pg_dump** — enter the PostgreSQL host, user, and password
4. Configure database selection (single DB, a list, or auto-discover all)
5. Click **Test Connection** to verify connectivity
6. Save the instance

## Step 5: Create a Backup Schedule

From the Instance Detail page, click **+ Add Job**:

1. Name the job (e.g., "Daily at 2am")
2. Set the cron expression using the visual builder or raw cron syntax
3. Enable the job and save

The first scheduled run will execute automatically. You can also click **Run now** at any time to test.

## Step 6: Set Up Notifications (Optional)

1. Create an SMTP or Telegram channel in **Channels**
2. On the Instance Detail page, scroll to the notification bindings section
3. Bind the channel to the instance and choose whether to receive success and/or failure notifications

## Setup Checklist

The app displays a setup banner until these items are completed:

- [ ] Timezone explicitly confirmed (not just the default UTC)
- [ ] At least one SMTP channel configured
- [ ] Password recovery email and channel set

Once all three are done, the banner disappears.
