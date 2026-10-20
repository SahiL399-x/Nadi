export function pollInterval(active: boolean, ms: number): number | false {
  return active ? ms : false;
}
