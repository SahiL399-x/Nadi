import { spawnSync } from 'node:child_process';
import { apiUrl, updateLocalEnv } from './local-network.mjs';

const url = apiUrl();
updateLocalEnv(url);
console.log(`Using API server: ${url}`);

const command = process.platform === 'win32' ? 'npx.cmd' : 'npx';
const result = spawnSync(command, ['expo', 'start', '--dev-client', '--lan'], {
  stdio: 'inherit',
  env: { ...process.env, EXPO_PUBLIC_API_URL: url },
});

process.exit(result.status ?? 1);
