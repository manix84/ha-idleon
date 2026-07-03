import { existsSync, readdirSync, readFileSync, renameSync } from "node:fs";
import path from "node:path";

const MONSTERS_DATA_PATH = "examples/websiteData/monsters.json";
const MONSTER_ASSETS_DIR = "assets/monsters";

const ALIASES: Record<string, string> = {
  board_bean: "bored_bean",
  pirate_captain: "dreadnaught_captain",
  jellyfish: "jellofish",
  rift: "the_rift",
};

type MonsterRecord = {
  Name?: unknown;
};

type CanonicalMonsterName = {
  slug: string;
};

type RenamePlan = {
  source: string;
  target: string;
};

type Conflict = {
  source: string;
  target: string;
  reason: string;
};

const args = new Set(process.argv.slice(2));
const dryRun = args.has("--dry-run");

if (args.has("--help") || args.has("-h")) {
  console.log(`Usage: tsx tools/rename-monster-assets.ts [--dry-run]

Safely renames assets/monsters/*.png name portions to canonical monster names.
Numeric filename prefixes are preserved.`);
  process.exit(0);
}

const canonicalMonsterNames = loadCanonicalMonsterNames(MONSTERS_DATA_PATH);
const assetFiles = readdirSync(MONSTER_ASSETS_DIR)
  .filter((filename) => filename.toLowerCase().endsWith(".png"))
  .sort((left, right) => left.localeCompare(right));

const plannedRenames: RenamePlan[] = [];
const unknown: string[] = [];
const conflicts: Conflict[] = [];
let alreadyCorrect = 0;

const targetOwners = new Map<string, string>();

for (const filename of assetFiles) {
  const parsed = parseMonsterAssetFilename(filename);
  const normalizedName = normalizeName(parsed.name);
  const canonicalKey = ALIASES[normalizedName] ?? normalizedName;
  const canonicalName = canonicalMonsterNames.get(canonicalKey);

  if (!canonicalName) {
    unknown.push(filename);
    continue;
  }

  const target = `${parsed.prefix}${canonicalName.slug}.png`;
  if (target === filename) {
    alreadyCorrect += 1;
    continue;
  }

  if (existsSync(path.join(MONSTER_ASSETS_DIR, target))) {
    conflicts.push({
      source: filename,
      target,
      reason: "target already exists",
    });
    continue;
  }

  const previousOwner = targetOwners.get(target);
  if (previousOwner) {
    conflicts.push({
      source: filename,
      target,
      reason: `duplicate target also proposed by ${previousOwner}`,
    });
    continue;
  }

  targetOwners.set(target, filename);
  plannedRenames.push({ source: filename, target });
}

for (const conflict of conflicts) {
  console.log(
    `Conflict: ${conflict.source} -> ${conflict.target} (${conflict.reason})`,
  );
}

for (const filename of unknown) {
  console.log(`Unknown: ${filename}`);
}

for (const rename of plannedRenames) {
  const line = `${rename.source} -> ${rename.target}`;
  if (dryRun) {
    console.log(`Would rename: ${line}`);
    continue;
  }

  renameSync(
    path.join(MONSTER_ASSETS_DIR, rename.source),
    path.join(MONSTER_ASSETS_DIR, rename.target),
  );
  console.log(`Renamed: ${line}`);
}

console.log("");
console.log(`Already correct: ${alreadyCorrect}`);
console.log(`Renamed: ${plannedRenames.length}`);
console.log(`Unknown: ${unknown.length}`);
console.log(`Conflicts: ${conflicts.length}`);

function loadCanonicalMonsterNames(
  monstersDataPath: string,
): Map<string, CanonicalMonsterName> {
  const rawData = JSON.parse(readFileSync(monstersDataPath, "utf8")) as Record<
    string,
    MonsterRecord
  >;
  const names = new Map<string, CanonicalMonsterName>();

  for (const monster of Object.values(rawData)) {
    if (!monster || typeof monster.Name !== "string" || !monster.Name) {
      continue;
    }

    const normalizedName = normalizeName(monster.Name);
    if (names.has(normalizedName)) {
      continue;
    }

    names.set(normalizedName, {
      slug: normalizedName,
    });
  }

  return names;
}

function parseMonsterAssetFilename(filename: string): {
  prefix: string;
  name: string;
} {
  const stem = filename.replace(/\.png$/i, "");
  const match = stem.match(/^(\d+_)(.+)$/);
  if (!match) {
    return { prefix: "", name: stem };
  }

  return { prefix: match[1], name: match[2] };
}

function normalizeName(value: string): string {
  return value
    .toLowerCase()
    .replace(/[\s_-]+/g, "_")
    .replace(/[^a-z0-9_]/g, "")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "");
}
