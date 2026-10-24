#!/usr/bin/env bash
# Sulvana installer for Linux (x86_64).
#
# Downloads the inference runtime (llama.cpp) and the models, builds the interface and adds Sulvana
# to the app menu and as a `sulvana` command. Safe to run again: anything already in place is kept,
# and interrupted downloads resume.
#
#   ./install.sh                     install Sulvana (asks before each download)
#   ./install.sh --yes               install without questions (core only, unless --with/--all)
#   ./install.sh --with voice,vision optional extras: voice, vision, images, nllb
#   ./install.sh --all               everything
#   ./install.sh --gpu cuda          llama.cpp build: vulkan (default, any GPU), cuda (NVIDIA) or cpu
#   ./install.sh --check             show what is installed and what is missing; changes nothing
#   ./install.sh --uninstall         remove the app-menu entry and the `sulvana` command (keeps this folder)
set -euo pipefail

APP="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
cd "$APP"

# Pinned versions: the exact builds Sulvana is developed and tested with.
LLAMA_BUILD=b11175
SD_TAG=master-913-b167b94
SD_ZIP=sd-master-b167b94-bin-Linux-Ubuntu-24.04-x86_64-vulkan.zip
HF=https://huggingface.co
DOWNLOADS="$APP/.runtime/downloads"

# Model files: "folder | Hugging Face repo | file in the repo | file name here | size in bytes (0 = small)".
CORE_FILES=(
  "models/MiMo-V2.6-Distill-Qwen-9B|bartowski/MiMo-V2.6-Distill-Qwen-9B-GGUF|MiMo-V2.6-Distill-Qwen-9B-Q4_K_M.gguf|MiMo-V2.6-Distill-Qwen-9B-Q4_K_M.gguf|5841049120"
  "models/hy-mt2-1.8b|tencent/Hy-MT2-1.8B-GGUF|Hy-MT2-1.8B-Q8_0.gguf|Hy-MT2-1.8B-Q8_0.gguf|1908528192"
)
VOICE_FILES=(
  "models/mms-tts-khm|facebook/mms-tts-khm|model.safetensors|model.safetensors|145255160"
  "models/mms-tts-khm|facebook/mms-tts-khm|config.json|config.json|0"
  "models/mms-tts-khm|facebook/mms-tts-khm|vocab.json|vocab.json|0"
  "models/mms-tts-khm|facebook/mms-tts-khm|tokenizer_config.json|tokenizer_config.json|0"
  "models/mms-tts-khm|facebook/mms-tts-khm|special_tokens_map.json|special_tokens_map.json|0"
)
VISION_FILES=(
  "models/Qwen2.5-VL-3B|unsloth/Qwen2.5-VL-3B-Instruct-GGUF|Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf|Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf|1929901408"
  "models/Qwen2.5-VL-3B|unsloth/Qwen2.5-VL-3B-Instruct-GGUF|mmproj-F16.gguf|mmproj-F16.gguf|1338428256"
)
IMAGES_FILES=(
  "models/Z-Image-Turbo|unsloth/Z-Image-Turbo-GGUF|z-image-turbo-Q4_K_M.gguf|z-image-turbo-Q4_K_M.gguf|5017613376"
  "models/Z-Image-Turbo|unsloth/Qwen3-4B-Instruct-2507-GGUF|Qwen3-4B-Instruct-2507-Q4_K_M.gguf|Qwen3-4B-Instruct-2507-Q4_K_M.gguf|2497281120"
  "models/Z-Image-Turbo|Tongyi-MAI/Z-Image-Turbo|vae/diffusion_pytorch_model.safetensors|vae.safetensors|167666902"
)
NLLB_FILES=(
  "models/nllb-200-1.3B-ct2-int8|OpenNMT/nllb-200-distilled-1.3B-ct2-int8|model.bin|model.bin|1377755738"
  "models/nllb-200-1.3B-ct2-int8|OpenNMT/nllb-200-distilled-1.3B-ct2-int8|config.json|config.json|0"
  "models/nllb-200-1.3B-ct2-int8|OpenNMT/nllb-200-distilled-1.3B-ct2-int8|generation_config.json|generation_config.json|0"
  "models/nllb-200-1.3B-ct2-int8|OpenNMT/nllb-200-distilled-1.3B-ct2-int8|shared_vocabulary.json|shared_vocabulary.json|0"
  "models/nllb-200-1.3B-ct2-int8|OpenNMT/nllb-200-distilled-1.3B-ct2-int8|special_tokens_map.json|special_tokens_map.json|0"
  "models/nllb-200-1.3B-ct2-int8|OpenNMT/nllb-200-distilled-1.3B-ct2-int8|tokenizer_config.json|tokenizer_config.json|0"
  "models/nllb-200-1.3B-ct2-int8|OpenNMT/nllb-200-distilled-1.3B-ct2-int8|tokenizer.json|tokenizer.json|0"
)
declare -A EXTRA_INFO=(
  [voice]="Read aloud: Meta's MMS Khmer voice (145 MB) and PyTorch for the CPU (about 1 GB of Python packages)"
  [vision]="Questions about images: Qwen2.5-VL 3B (3.3 GB)"
  [images]="Image creation with /image: Z-Image Turbo (7.7 GB) and stable-diffusion.cpp"
  [nllb]="Backup Khmer translator: NLLB-200 1.3B (1.4 GB) and its Python packages (about 0.6 GB)"
)
EXTRAS_ORDER=(voice vision images nllb)

# ---------- output ----------
if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then B=$'\e[1m'; G=$'\e[32m'; Y=$'\e[33m'; R=$'\e[31m'; D=$'\e[2m'; N=$'\e[0m'; else B= G= Y= R= D= N=; fi
step() { printf '\n%s==> %s%s\n' "$B" "$*" "$N"; }
ok()   { printf '  %s✓%s %s\n' "$G" "$N" "$*"; }
warn() { printf '  %s!%s %s\n' "$Y" "$N" "$*"; }
fail() { printf '  %s✗%s %s\n' "$R" "$N" "$*"; }
die()  { printf '\n%sError:%s %s\n' "$R" "$N" "$*" >&2; exit 1; }
human() { awk -v b="$1" 'BEGIN { split("B KB MB GB TB", u, " "); i = 1; while (b >= 1000 && i < 5) { b /= 1000; i++ } printf (i == 1 ? "%d %s" : "%.1f %s"), b, u[i] }'; }
ask() {  # ask "question" default(y/n)
  local answer
  [[ "$ASSUME_YES" == 1 || ! -t 0 ]] && { [[ "$2" == y ]]; return; }
  read -r -p "  $1 [$([[ $2 == y ]] && echo Y/n || echo y/N)] " answer || true
  answer="${answer:-$2}"
  [[ "${answer,,}" == y* ]]
}

# ---------- arguments ----------
ASSUME_YES=0; MODE=install; GPU=vulkan; WANT=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes) ASSUME_YES=1 ;;
    --all) WANT=("${EXTRAS_ORDER[@]}") ;;
    --with) shift; IFS=',' read -r -a more <<< "${1:-}"; WANT+=("${more[@]}") ;;
    --with=*) IFS=',' read -r -a more <<< "${1#--with=}"; WANT+=("${more[@]}") ;;
    --gpu) shift; GPU="${1:-}" ;;
    --gpu=*) GPU="${1#--gpu=}" ;;
    --check) MODE=check ;;
    --uninstall) MODE=uninstall ;;
    -h|--help) sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "Unknown option: $1 (see ./install.sh --help)" ;;
  esac
  shift
done
for extra in "${WANT[@]}"; do
  [[ -n "${EXTRA_INFO[$extra]:-}" ]] || die "Unknown extra '$extra'. Choose from: ${EXTRAS_ORDER[*]}"
done
case "$GPU" in
  vulkan) LLAMA_ASSET="llama-$LLAMA_BUILD-bin-ubuntu-vulkan-x64.tar.gz" ;;
  cuda) LLAMA_ASSET="llama-$LLAMA_BUILD-bin-ubuntu-cuda-13.4-x64.tar.gz" ;;
  cpu) LLAMA_ASSET="llama-$LLAMA_BUILD-bin-ubuntu-x64.tar.gz" ;;
  *) die "--gpu must be vulkan, cuda or cpu" ;;
esac

files_of() { local name="${1^^}_FILES[@]"; printf '%s\n' "${!name}"; }
have_file() {  # have_file "folder|repo|remote|local|bytes"
  local folder repo remote local_name bytes path
  IFS='|' read -r folder repo remote local_name bytes <<< "$1"
  path="$APP/$folder/$local_name"
  [[ -f "$path" ]] && { [[ "$bytes" == 0 ]] || [[ "$(stat -L -c %s "$path")" == "$bytes" ]]; }
}
component_ready() { local spec; while IFS= read -r spec; do have_file "$spec" || return 1; done < <(files_of "$1"); }
missing_bytes() {
  local spec total=0 folder repo remote local_name bytes
  while IFS= read -r spec; do
    have_file "$spec" && continue
    IFS='|' read -r folder repo remote local_name bytes <<< "$spec"
    local part="$APP/$folder/$local_name.part" done_bytes=0
    [[ -f "$part" ]] && done_bytes="$(stat -c %s "$part")"
    total=$((total + bytes - done_bytes))
  done < <(files_of "$1")
  echo "$total"
}
python_has() { "$1" -c "import importlib.util, sys; sys.exit(0 if all(importlib.util.find_spec(m) for m in sys.argv[1:]) else 1)" "${@:2}" 2>/dev/null; }
venv_python() { [[ -x "$APP/.venv/bin/python" ]] && echo "$APP/.venv/bin/python" || command -v python3 || true; }
launcher_path="$HOME/.local/bin/sulvana"
desktop_path="${XDG_DATA_HOME:-$HOME/.local/share}/applications/sulvana.desktop"

# ---------- uninstall ----------
if [[ "$MODE" == uninstall ]]; then
  step "Removing Sulvana from the app menu"
  "$APP/sulvana-native.sh" stop >/dev/null 2>&1 || true
  ok "Engine stopped"
  if [[ -f "$launcher_path" ]] && grep -q "$APP/sulvana-native.sh" "$launcher_path"; then rm -f "$launcher_path"; ok "Removed $launcher_path"; fi
  if [[ -f "$desktop_path" ]] && grep -q "$APP" "$desktop_path"; then rm -f "$desktop_path"; ok "Removed $desktop_path"; fi
  echo
  echo "Your conversations live in the app window's storage; the models and this folder are untouched."
  echo "To delete everything, remove this folder: rm -rf \"$APP\""
  exit 0
fi

# ---------- check ----------
check_report() {
  step "Sulvana in $APP"
  local all_ok=0
  if [[ -x "$APP/vision-runner/llama-server" ]]; then ok "Inference runtime (llama.cpp)"; else fail "Inference runtime (llama.cpp) is missing"; all_ok=1; fi
  if component_ready core; then ok "Chat model and Khmer tools model"; else fail "Models still to download: $(human "$(missing_bytes core)")"; all_ok=1; fi
  if [[ -f "$APP/sulvana-ui/dist/index.html" ]]; then ok "Interface built"; else fail "Interface not built"; all_ok=1; fi
  if [[ -f "$APP/runs/finetune/mimo-khmer-v2/mimo-khmer-v2.gguf" && -f "$APP/runs/finetune/mimo-khmer-01/sulvana-khmer-mimo-01.gguf" ]]; then
    ok "Khmer adapters (WKH Labs fine-tunes)"
  else
    warn "Khmer adapters not present: Sulvana runs the base model (they are not published for download yet)"
  fi
  local py; py="$(venv_python)"
  for extra in "${EXTRAS_ORDER[@]}"; do
    local ready=0
    component_ready "$extra" || ready=1
    case "$extra" in
      voice) python_has "$py" torch transformers numpy || ready=1 ;;
      nllb) python_has "$py" ctranslate2 transformers sentencepiece || ready=1 ;;
      images) [[ -x "$APP/z-image-runner/sd-cli" ]] || ready=1 ;;
    esac
    if [[ $ready == 0 ]]; then ok "Extra: $extra"; else printf '  %s-%s Extra not installed: %s %s(./install.sh --with %s)%s\n' "$D" "$N" "$extra" "$D" "$extra" "$N"; fi
  done
  if [[ -f "$launcher_path" ]]; then ok "'sulvana' command and app-menu entry"; else warn "No 'sulvana' command yet"; fi
  return $all_ok
}
if [[ "$MODE" == check ]]; then
  check_report && { echo; echo "Ready: run 'sulvana' (or open Sulvana from the app menu)."; } || { echo; echo "Run ./install.sh to finish installing."; exit 1; }
  exit 0
fi

# ---------- 1. this computer ----------
step "Checking this computer"
[[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 ]] || die "This installer supports Linux on x86_64 for now (found $(uname -s) $(uname -m))."
for tool in curl tar; do command -v "$tool" >/dev/null || die "Please install '$tool' first."; done
PYTHON="$(command -v python3 || true)"
[[ -n "$PYTHON" ]] || die "Please install Python 3.10 or newer (package 'python3' or 'python')."
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || die "Sulvana needs Python 3.10 or newer (found $("$PYTHON" -V 2>&1))."
ok "$("$PYTHON" -V 2>&1)"
NODE_OK=0
if command -v node >/dev/null && command -v npm >/dev/null && node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>22||(a==22&&b>=12)||(a==20&&b>=19)?0:1)'; then
  NODE_OK=1; ok "Node.js $(node -v) (to build the interface)"
elif [[ -f "$APP/sulvana-ui/dist/index.html" ]]; then
  warn "Node.js 20.19+ not found; using the interface that is already built"
else
  die "Node.js 20.19 or newer is needed once, to build the interface.
  Arch/CachyOS: sudo pacman -S nodejs npm      Fedora: sudo dnf install nodejs npm
  Debian/Ubuntu: the packaged Node.js is often too old; use https://nodejs.org or 'nvm install --lts'"
fi
if command -v nvidia-smi >/dev/null && nvidia-smi --query-gpu=name,memory.total --format=csv,noheader >/dev/null 2>&1; then
  IFS=',' read -r gpu_name gpu_mem <<< "$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits | head -1)"
  gpu_mem="${gpu_mem// /}"
  ok "GPU: ${gpu_name} ($(((gpu_mem + 512) / 1024)) GB)"
  (( gpu_mem >= 7500 )) || warn "Sulvana is tuned for 8 GB of GPU memory; with less it still runs, but part of the model moves to system RAM and replies are slower."
else
  warn "No NVIDIA GPU found with nvidia-smi. AMD and Intel GPUs work through Vulkan; without a GPU, Sulvana runs slowly on the CPU."
fi
free_bytes="$(df --output=avail -B1 "$APP" | tail -1)"
ok "Free disk space here: $(human "$free_bytes")"

# ---------- 2. what to download ----------
if [[ ${#WANT[@]} -eq 0 && "$ASSUME_YES" == 0 && -t 0 ]]; then
  step "Optional extras (you can add them later with ./install.sh --with <name>)"
  for extra in "${EXTRAS_ORDER[@]}"; do
    if component_ready "$extra" && { [[ "$extra" != images ]] || [[ -x "$APP/z-image-runner/sd-cli" ]]; }; then continue; fi
    ask "${EXTRA_INFO[$extra]}?" n && WANT+=("$extra")
  done
fi
COMPONENTS=(core "${WANT[@]}")
total=0
step "Downloads"
for component in "${COMPONENTS[@]}"; do
  need="$(missing_bytes "$component")"
  if [[ "$need" -gt 0 ]]; then
    printf '  %-8s %s\n' "$component" "$(human "$need")"
    total=$((total + need))
  else
    ok "$component models already downloaded"
  fi
done
[[ -x "$APP/vision-runner/llama-server" ]] || { printf '  %-8s %s\n' runtime "about 31 MB (llama.cpp $LLAMA_BUILD, $GPU)"; total=$((total + 31000000)); }
[[ " ${COMPONENTS[*]} " == *" images "* && ! -x "$APP/z-image-runner/sd-cli" ]] && { printf '  %-8s %s\n' sd.cpp "39 MB (image runtime)"; total=$((total + 38629328)); }
if [[ $total -gt 0 ]]; then
  echo "  Total: $(human "$total"), from Hugging Face and GitHub."
  (( free_bytes > total + 2000000000 )) || die "Not enough free disk space: $(human "$total") to download plus about 2 GB to spare, $(human "$free_bytes") free."
  ask "Download now?" y || die "Nothing downloaded. Run ./install.sh again when you are ready."
fi

download() {  # download "folder|repo|remote|local|bytes"
  local folder repo remote local_name bytes dest part have
  IFS='|' read -r folder repo remote local_name bytes <<< "$1"
  have_file "$1" && return 0
  dest="$APP/$folder/$local_name"; part="$dest.part"
  mkdir -p "$APP/$folder"
  printf '  %s %s(%s)%s\n' "$local_name" "$D" "$( [[ $bytes == 0 ]] && echo small || human "$bytes")" "$N"
  have=0; [[ -f "$part" ]] && have="$(stat -c %s "$part")"
  if [[ "$bytes" == 0 || "$have" -lt "$bytes" ]]; then
    curl -fL --retry 5 --retry-delay 3 --connect-timeout 20 $( [[ "$bytes" -gt 50000000 && -t 1 ]] && echo --progress-bar || echo -sS ) \
      $( [[ "$have" -gt 0 ]] && echo "-C -" ) -o "$part" "$HF/$repo/resolve/main/$remote" \
      || die "Could not download $local_name. Check your connection and run ./install.sh again; it resumes where it stopped."
  fi
  if [[ "$bytes" != 0 && "$(stat -c %s "$part")" != "$bytes" ]]; then
    rm -f "$part"; die "$local_name did not download completely. Run ./install.sh again."
  fi
  mv -f "$part" "$dest"
}

# ---------- 3. inference runtime ----------
step "Inference runtime"
if [[ -x "$APP/vision-runner/llama-server" ]]; then
  ok "llama.cpp is installed ($("$APP/vision-runner/llama-server" --version 2>&1 | grep -o 'build [0-9]*' | head -1))"
else
  mkdir -p "$DOWNLOADS"; rm -rf "$DOWNLOADS/llama"
  curl -fL --retry 5 -sS -o "$DOWNLOADS/$LLAMA_ASSET" "https://github.com/ggml-org/llama.cpp/releases/download/$LLAMA_BUILD/$LLAMA_ASSET" \
    || die "Could not download llama.cpp ($LLAMA_ASSET)."
  mkdir -p "$DOWNLOADS/llama" && tar -xzf "$DOWNLOADS/$LLAMA_ASSET" -C "$DOWNLOADS/llama"
  server="$(find "$DOWNLOADS/llama" -type f -name llama-server | head -1)"
  [[ -n "$server" ]] || die "The llama.cpp download did not contain llama-server."
  mkdir -p "$APP/vision-runner" && cp -a "$(dirname "$server")"/. "$APP/vision-runner/"
  rm -rf "$DOWNLOADS/llama" "$DOWNLOADS/$LLAMA_ASSET"
  ok "llama.cpp $LLAMA_BUILD ($GPU) installed in vision-runner/"
fi
if devices="$("$APP/vision-runner/llama-server" --list-devices 2>/dev/null)" && grep -qiE 'vulkan|cuda' <<< "$devices"; then
  ok "GPU found by llama.cpp: $(grep -iE 'vulkan|cuda' <<< "$devices" | head -1 | sed 's/^[[:space:]]*//')"
elif [[ "$GPU" != cpu ]]; then
  warn "llama.cpp did not find a GPU, so Sulvana will run on the CPU (slow)."
  [[ "$GPU" == vulkan ]] && warn "Install your GPU's Vulkan driver and run ./install.sh again:
      Arch/CachyOS: sudo pacman -S vulkan-icd-loader (plus nvidia-utils, vulkan-radeon or vulkan-intel)
      Debian/Ubuntu: sudo apt install libvulkan1 mesa-vulkan-drivers   (NVIDIA's own driver includes Vulkan)"
fi

# ---------- 4. models ----------
for component in "${COMPONENTS[@]}"; do
  step "Models: $component"
  if component_ready "$component"; then ok "Already downloaded"; continue; fi
  while IFS= read -r spec; do download "$spec"; done < <(files_of "$component")
  ok "Done"
done
if [[ " ${COMPONENTS[*]} " == *" images "* && ! -x "$APP/z-image-runner/sd-cli" ]]; then
  step "Image runtime (stable-diffusion.cpp)"
  command -v unzip >/dev/null || die "Please install 'unzip' for the image runtime."
  mkdir -p "$DOWNLOADS"; rm -rf "$DOWNLOADS/sd"
  curl -fL --retry 5 -sS -o "$DOWNLOADS/$SD_ZIP" "https://github.com/leejet/stable-diffusion.cpp/releases/download/$SD_TAG/$SD_ZIP" \
    || die "Could not download stable-diffusion.cpp."
  unzip -q -o "$DOWNLOADS/$SD_ZIP" -d "$DOWNLOADS/sd"
  cli="$(find "$DOWNLOADS/sd" -type f -name sd-cli | head -1)"
  [[ -n "$cli" ]] || die "The stable-diffusion.cpp download did not contain sd-cli."
  mkdir -p "$APP/z-image-runner" && cp -a "$(dirname "$cli")"/. "$APP/z-image-runner/" && chmod +x "$APP/z-image-runner/sd-cli"
  rm -rf "$DOWNLOADS/sd" "$DOWNLOADS/$SD_ZIP"
  ok "stable-diffusion.cpp installed in z-image-runner/"
fi

# ---------- 5. Python packages for the extras ----------
# The chat itself needs only Python's standard library. The voice and the backup translator need
# PyTorch / Transformers / CTranslate2, installed into a private environment in .venv.
py_packages=()
[[ " ${COMPONENTS[*]} " == *" voice "* ]] && py_packages+=(torch transformers numpy)
[[ " ${COMPONENTS[*]} " == *" nllb "* ]] && py_packages+=(ctranslate2 transformers sentencepiece)
if [[ ${#py_packages[@]} -gt 0 ]]; then
  step "Python packages for the extras"
  if [[ ! -x "$APP/.venv/bin/python" ]]; then
    "$PYTHON" -m venv "$APP/.venv" || die "Could not create a Python environment. On Debian/Ubuntu: sudo apt install python3-venv"
  fi
  VPY="$APP/.venv/bin/python"
  missing=()
  for package in "${py_packages[@]}"; do python_has "$VPY" "$package" || missing+=("$package"); done
  if [[ ${#missing[@]} -eq 0 ]]; then
    ok "Already installed"
  else
    "$VPY" -m pip install --quiet --upgrade pip || true
    if [[ " ${missing[*]} " == *" torch "* ]]; then
      # The CPU build: the voice runs on the CPU, and this keeps the download small.
      "$VPY" -m pip install --quiet --index-url https://download.pytorch.org/whl/cpu torch || warn "PyTorch could not be installed; the voice will stay off."
    fi
    rest=(); for package in "${missing[@]}"; do [[ "$package" == torch ]] || rest+=("$package"); done
    rest=($(printf '%s\n' "${rest[@]}" | sort -u))
    if [[ ${#rest[@]} -gt 0 ]]; then
      "$VPY" -m pip install --quiet "${rest[@]}" || warn "Some Python packages could not be installed: ${rest[*]}"
    fi
    ok "Installed: ${missing[*]}"
  fi
fi

# ---------- 6. interface ----------
step "Interface"
if [[ "$NODE_OK" == 1 ]]; then
  (cd "$APP/sulvana-ui" && export NODE_OPTIONS=--no-deprecation && { [[ -d node_modules ]] || npm ci --no-audit --no-fund --loglevel=error >/dev/null; } && npm run build --silent >/dev/null) \
    || die "The interface could not be built. Try: cd sulvana-ui && npm ci && npm run build"
  ok "Built sulvana-ui/dist/"
else
  ok "Using the existing build"
fi

# ---------- 7. app menu and command ----------
step "App menu and the 'sulvana' command"
mkdir -p "$(dirname "$launcher_path")" "$(dirname "$desktop_path")"
if [[ -f "$launcher_path" ]] && ! grep -q "sulvana-native.sh" "$launcher_path"; then
  mv "$launcher_path" "$launcher_path.bak"; warn "Kept your previous $launcher_path as sulvana.bak"
fi
printf '#!/usr/bin/env bash\nexec "%s/sulvana-native.sh" "$@"\n' "$APP" > "$launcher_path"
chmod +x "$launcher_path" "$APP/sulvana-native.sh" "$APP/sulvana-web.sh"
cat > "$desktop_path" <<EOF
[Desktop Entry]
Type=Application
Name=Sulvana
GenericName=AI assistant
Comment=Khmer-first AI assistant that runs on this computer
Exec=$launcher_path
Icon=$APP/sulvana-icon.png
Terminal=false
Categories=Education;Utility;
StartupNotify=true
StartupWMClass=Sulvana
EOF
command -v update-desktop-database >/dev/null && update-desktop-database "$(dirname "$desktop_path")" >/dev/null 2>&1 || true
ok "Added 'Sulvana' to the app menu"
ok "Added the command $launcher_path"
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) warn "$HOME/.local/bin is not on your PATH, so type the full path or add it (fish: fish_add_path ~/.local/bin)";; esac
if ! command -v electron >/dev/null && ! [[ -x "$APP/electron-ui/node_modules/.bin/electron" ]]; then
  warn "Electron is not installed, so Sulvana opens in a browser window (Chromium/Chrome app mode if available)."
fi

check_report >/dev/null || true
step "Done"
echo "  Open Sulvana from the app menu, or run:  sulvana"
echo "  Stop it (frees GPU memory, e.g. before gaming):  sulvana stop"
echo "  See what is installed:  ./install.sh --check"
