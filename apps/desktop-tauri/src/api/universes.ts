import { requestJson } from './requestJson';

interface UniverseMemberRecord {
  symbol?: string;
  ticker?: string;
}

interface UniverseMembersResponse {
  members?: Array<string | UniverseMemberRecord>;
  symbols?: string[];
}

export async function fetchUniverseSymbols(baseUrl: string, universeId: string): Promise<string[]> {
  const normalizedUniverseId = universeId.trim();
  if (!normalizedUniverseId) {
    return [];
  }

  const payload = await requestJson<UniverseMembersResponse>(
    baseUrl,
    `/api/v1/control-plane/universes/${encodeURIComponent(normalizedUniverseId)}/members`,
  );

  const rawMembers = Array.isArray(payload.members)
    ? payload.members
    : Array.isArray(payload.symbols)
      ? payload.symbols
      : [];

  const extractedSymbols = rawMembers
    .map((member) => {
      if (typeof member === 'string') {
        return member;
      }
      if (member && typeof member === 'object') {
        return member.symbol ?? member.ticker ?? '';
      }
      return '';
    })
    .map((symbol) => symbol.trim().toUpperCase())
    .filter(Boolean);

  return Array.from(new Set(extractedSymbols));
}
