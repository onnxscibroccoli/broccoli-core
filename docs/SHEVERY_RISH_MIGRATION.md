# Shevery rish migration — Samsung SM-A146U

## Verified evidence

On 2026-10-07 the user reported Shevery 14.1.0 (41), Android 15 / SDK 35, server UID 2000, API 14.1, SELinux u:r:shell:s0, no root, and service running. The original rish command repeatedly timed out.

An isolated launcher/DEX pair copied into Termux private storage at ~/rish-shevery-test.l9BdrI, with RISH_APPLICATION_ID=com.termux and DEX mode 400, returned uid=2000(shell). After installing a $PREFIX/bin/rish wrapper pointing to that pair, the user verified:

```text
BROCCOLI_RISH_OK
SM-A146U
```

The recovery is verified by user-provided live output. The exact original cause (PATH selection, DEX mismatch, or another manager boundary) was not isolated. Battery restrictions were not established as the cause.

## Permanent path

The following finalization moves a copy of the tested pair to ~/.local/lib/broccoli/rish and updates $PREFIX/bin/rish. It preserves the previously working wrapper. This permanent-path step still requires execution on the phone; it is not part of the reported proof above.

```bash
bash <<'BASH'
set -eu
src="$HOME/rish-shevery-test.l9BdrI"
dst="$HOME/.local/lib/broccoli/rish"
test -s "$src/rish"
test -s "$src/rish_shizuku.dex"
test ! -e "$dst" || { echo "Destination exists; stopped without overwriting."; exit 1; }
mkdir -p "$dst"
cp "$src/rish" "$dst/rish"
cp "$src/rish_shizuku.dex" "$dst/rish_shizuku.dex"
chmod 700 "$dst" "$dst/rish"
chmod 400 "$dst/rish_shizuku.dex"
backup="$(mktemp -d "$HOME/rish-backup.XXXXXX")"
cp -a "$PREFIX/bin/rish" "$backup/rish"
wrapper="$(mktemp "$PREFIX/bin/.rish-wrapper.XXXXXX")"
cat > "$wrapper" <<'SH'
#!/data/data/com.termux/files/usr/bin/sh
export RISH_APPLICATION_ID=com.termux
exec /system/bin/sh /data/data/com.termux/files/home/.local/lib/broccoli/rish/rish "$@"
SH
chmod 700 "$wrapper"
mv -f "$wrapper" "$PREFIX/bin/rish"
printf 'Rollback copy: %s/rish\n' "$backup"
BASH
hash -r
rish -c 'id'
rish -c 'printf "BROCCOLI_RISH_OK\n"; getprop ro.product.model'
```

Do not delete the tested directory until permanent-path verification succeeds. Rollback by copying the printed backup/rish to $PREFIX/bin/rish.

## Broccoli and RDC

lib/rish_run.sh already defaults to /data/data/com.termux/files/usr/bin/rish; no transport code change is required. RISH_APPLICATION_ID remains com.termux, the requesting terminal app, rather than the manager package.

For background/RDC execution continue using tools.android_transport.RishTransport, which re-enters Termux through RunCommandService. Direct foreground rish proof does not establish RDC transport proof.

After syncing this branch on the phone:

```bash
cd "$HOME/broccoli-core"
bash lib/rish_transport_probe.sh
```

The probe records target evidence at /sdcard/OmniKali/broccoli/rish-transport-proof.txt. Any cached PASS must remain bound to the actual launcher/DEX, code, and transport; do not reuse a prior manager's PASS.

## Maintenance

Export future rish/DEX pairs from the installed manager, stage them in Termux private storage, enforce read-only DEX permissions, and verify uid=2000 before replacing the working wrapper. Keep DEX files and device runtime environment captures out of Git.

Reference: https://github.com/HmnDev-Tech/shevery . Its migration guidance describes the manager package change and conflicts with older official Shizuku installations; installed-manager coexistence was not inspected in this session.
