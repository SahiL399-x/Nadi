import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { apiUrl, updateLocalEnv } from './local-network.mjs';

const mobileRoot = process.cwd();
const easPath = path.join(mobileRoot, 'eas.json');
const url = apiUrl();
updateLocalEnv(url);
const eas = JSON.parse(fs.readFileSync(easPath, 'utf8'));

eas.build ??= {};
eas.build.development ??= {};
eas.build.development.env ??= {};
eas.build.development.env.EXPO_PUBLIC_API_URL = url;
fs.writeFileSync(easPath, `${JSON.stringify(eas, null, 2)}\n`);

console.log(`Using API server: ${url}`);
console.log('Starting EAS development Android build...');

const command = process.platform === 'win32' ? 'npx.cmd' : 'npx';
const result = spawnSync(command, ['eas-cli', 'build', '--profile', 'development', '--platform', 'android'], {
  cwd: mobileRoot,
  stdio: 'inherit',
  env: { ...process.env, EXPO_PUBLIC_API_URL: url },
  shell: process.platform === 'win32',
});

if (result.error) {
  console.error(`Could not start EAS CLI: ${result.error.message}`);
}

process.exit(result.status ?? 1);
