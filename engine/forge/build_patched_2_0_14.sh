#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 /path/to/forge-2.0.14-source" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
forge_source="$(cd "$1" && pwd)"
patch_file="$repo_root/engine/forge/patches/forge-2.0.14-mtg-agent.patch"
destination="$repo_root/engine/forge/dist/2.0.14/forge-gui-desktop-2.0.14-jar-with-dependencies.jar"

git -C "$forge_source" apply --check "$patch_file"
git -C "$forge_source" apply "$patch_file"

java_home="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home}"
PATH="$java_home/bin:$PATH" JAVA_HOME="$java_home" \
  mvn -q -f "$forge_source/pom.xml" \
  -pl forge-gui-desktop -am \
  -Dtest=forge.ai.WeSayTheeNayTest \
  -Dsurefire.failIfNoSpecifiedTests=false \
  test
PATH="$java_home/bin:$PATH" JAVA_HOME="$java_home" \
  mvn -q -f "$forge_source/pom.xml" \
  -pl forge-gui-desktop -am -DskipTests package

cp \
  "$forge_source/forge-gui-desktop/target/forge-gui-desktop-2.0.14-jar-with-dependencies.jar" \
  "$destination"
shasum -a 256 "$destination"
