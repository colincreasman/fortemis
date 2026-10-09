#!/bin/sh
# Builds every firmware image listed in build.yaml with ZMK's Docker image, the way GitHub Actions
# does (zmkfirmware/zmk build-user-config.yml), and writes them to firmware/<artifact>.uf2 with the
# same names as the Actions artifact.
#
# The west workspace (ZMK, Zephyr and modules, about 2 GB) is kept in the Docker volume
# fortemis-zmk, so only the first run, or a change to config/west.yml, downloads anything.
# Remove it with: docker volume rm fortemis-zmk
set -eu

repo=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$repo/firmware"

docker run --rm \
    -v fortemis-zmk:/workspace \
    -v "$repo":/repo:ro \
    -v "$repo/firmware":/out \
    zmkfirmware/zmk-build-arm:stable sh -euc '
cd /workspace
rm -rf config build
mkdir -p config build
cp -R /repo/config/. config/
if ! cmp -s config/west.yml .west.yml.done; then
    [ -d .west ] || west init -l config
    echo "Updating the west workspace (slow the first time)..."
    west update --fetch-opt=--filter=tree:0
    cp /repo/config/west.yml .west.yml.done
fi
west zephyr-export >/dev/null

python3 - <<EOF > targets
import yaml
for t in yaml.safe_load(open("/repo/build.yaml"))["include"]:
    board, shield = t["board"], t.get("shield", "")
    name = t.get("artifact-name") or (shield + "-" if shield else "") + board + "-zmk"
    print("|".join([name, board, shield, t.get("snippet", ""), t.get("cmake-args", "")]))
EOF

failed=0
rm -f /out/*.uf2
while IFS="|" read -r name board shield snippet cmake_args; do
    dir="build/$(echo "$name" | tr " " _)"
    set -- -s zmk/app -d "$dir" -b "$board"
    [ -n "$snippet" ] && set -- "$@" -S "$snippet"
    # cmake-args is split on spaces, as the Actions workflow does.
    if west build "$@" -- -DZMK_CONFIG=/workspace/config -DSHIELD="$shield" \
            -DZMK_EXTRA_MODULES=/repo $cmake_args < /dev/null > "$dir.log" 2>&1; then
        cp "$dir/zephyr/zmk.uf2" "/out/$name.uf2"
        echo "OK      $name.uf2"
    else
        echo "FAILED  $name"
        tail -n 30 "$dir.log"
        failed=1
    fi
done < targets
exit $failed
'
