#!/usr/bin/env bash
set -euo pipefail
# Unprivileged Debian 13 setup; signed APT metadata and package hashes stay enabled.
root=/workspace/emulator
mkdir -p "$root/apt/lists/partial" "$root/apt/cache/archives/partial" "$root/root"
cat > "$root/apt/sources.list" <<'SOURCES'
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie main
SOURCES
opts=(-o "Dir::Etc::sourcelist=$root/apt/sources.list" -o Dir::Etc::sourceparts=-
      -o "Dir::State::lists=$root/apt/lists" -o "Dir::Cache=$root/apt/cache"
      -o APT::Sandbox::User=agent)
apt-get "${opts[@]}" update
cd "$root/apt/cache/archives"
# Pin emulator version; auxiliary Debian packages resolve through signed metadata.
apt-get "${opts[@]}" download desmume=0.9.13-4 xvfb=2:21.1.16-1.3+deb13u3 xauth=1:1.1.2-1.1 libpcap0.8t64=1.10.5-2 libsoundtouch1=2.4.0+ds-1 libtinyxml2.6.2v5=2.6.2-7 libxfont2=1:2.0.6-1+deb13u1
for deb in ./*.deb; do dpkg-deb -x "$deb" "$root/root"; done
export LD_LIBRARY_PATH="$root/root/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export ALSOFT_DRIVERS=null
status=0
"$root/root/usr/games/desmume-cli" --help > "$root/help.txt" 2>&1 || status=$?
# This CLI returns 1 for --help; accept that documented observation only with
# the expected version and option text, not arbitrary failures.
if (( status > 1 )); then cat "$root/help.txt"; exit "$status"; fi
grep -q 'DeSmuME 0.9.13' "$root/help.txt"
grep -q -- '--disable-sound' "$root/help.txt"
# A future Debian release removing these versions is an explicit refresh task,
# never a reason to disable APT signatures or use an unverified binary.
