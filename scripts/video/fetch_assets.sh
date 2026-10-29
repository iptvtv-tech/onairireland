#!/usr/bin/env bash
# Downloads the data files the Shorts voice needs into $VIDEO_ASSETS
# (default ~/.cache/onair-video), and checks each against a pinned SHA-256.
#   kokoro.onnx, voices.bin  Kokoro v1.0 voice model and voices (thewh1teagle/kokoro-onnx release)
#   config.json              the model's phoneme symbol list (kokoro-onnx, pinned commit)
#   cmudict.dict             CMU pronouncing dictionary (cmusphinx/cmudict, pinned commit)
set -euo pipefail

DIR="${VIDEO_ASSETS:-$HOME/.cache/onair-video}"
mkdir -p "$DIR"

KOKORO_REL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
KOKORO_SHA="3596b26764286a7de9d90c363e988d50578918e5"
CMU_SHA="74790861f652b15e4ac49015a90074ad62a27690"

fetch() {  # name url sha256
  local name="$1" url="$2" sum="$3"
  if [ -f "$DIR/$name" ] && echo "$sum  $DIR/$name" | sha256sum -c --status; then
    echo "$name: cached"
    return
  fi
  curl -fsSL --retry 3 -o "$DIR/$name.part" "$url"
  echo "$sum  $DIR/$name.part" | sha256sum -c --status || {
    echo "$name: checksum mismatch, refusing to use it" >&2
    rm -f "$DIR/$name.part"
    exit 1
  }
  mv "$DIR/$name.part" "$DIR/$name"
  echo "$name: downloaded"
}

fetch kokoro.onnx  "$KOKORO_REL/kokoro-v1.0.onnx" 7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5
fetch voices.bin   "$KOKORO_REL/voices-v1.0.bin"  bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d
fetch config.json  "https://raw.githubusercontent.com/thewh1teagle/kokoro-onnx/$KOKORO_SHA/src/kokoro_onnx/config.json" \
                   5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f
fetch cmudict.dict "https://raw.githubusercontent.com/cmusphinx/cmudict/$CMU_SHA/cmudict.dict" \
                   81917843c7f44ce2b094ac63873c2c7a4cf802040792c455ba3ca406891c3d22
