export function normalizeSelectionMetadata(payload) {
  const count=payload.positions.length;
  if(payload.returned_positions!==undefined && payload.returned_positions!==count) {
    payload.source_scan_returned_positions ??= payload.returned_positions;
  }
  payload.returned_positions=count;
  return payload;
}
