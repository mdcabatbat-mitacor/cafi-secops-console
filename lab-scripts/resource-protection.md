# Resource Group Protection — rg-cafi-lab

## Access review (confirmed 2026-07-10)

Checked `rg-cafi-lab` → Access control (IAM) → Role assignments before applying any lock, to confirm
no unexpected account already held delete/write access.

Confirmed 6 role assignments, all accounted for:
- **Owner** — Michael Cabatbat (subscription-inherited) — the only human account with write/delete access
- **Azure AI Administrator** — `cafi-ml` managed identity, scoped to itself only ("This resource")
- **Microsoft Sentinel Contributor** (×2) — `Microsoft Threat Protection` and `WindowsDefenderATP`,
  Microsoft's own service principals for the Sentinel connectors enabled in Step 2 — not human accounts,
  and scoped to Sentinel-specific actions only (does not grant resource-group deletion rights)
- **User Access Administrator** — Michael Cabatbat (root-inherited)

`SysAD@mitacor.net` does not appear anywhere in this list — confirmed to hold no Azure RBAC role at
all. Their console Administrator role is an Entra **app role** for signing into the CAFI SecOps web
app; it is unrelated to Azure Resource Manager permissions and grants zero ability to modify or delete
any Azure resource.

```bash
# review command (read-only, safe to re-run any time)
az role assignment list --resource-group rg-cafi-lab -o table
```

## Delete lock

Applied a **Delete** lock (not Read-only — Read-only would have blocked all further build work,
including everything still ahead in Steps 6/7/9/10). A Delete lock only blocks deletion; normal
create/modify/configure operations continue to work exactly as before.

```bash
az lock create --name "cafi-lab-delete-lock" --resource-group rg-cafi-lab --lock-type CanNotDelete

# verify
az lock show --name "cafi-lab-delete-lock" --resource-group rg-cafi-lab
```

**Gotcha hit while applying this**: the portal's **+ Add** lock dialog defaults its Lock type dropdown
to **Read-only**, not Delete — easy to click through without noticing. Always double check the Lock
type column after creating a lock via the portal; the CLI command above avoids the mix-up entirely by
being explicit (`--lock-type CanNotDelete`).

Removing a lock (if ever needed) requires `Microsoft.Authorization/locks/*` permission, which is bundled
into Owner and Contributor — a lock is not "immune to everyone including the owner," it just requires
an explicit extra step (delete the lock, then delete the resource) rather than a single accidental click.
