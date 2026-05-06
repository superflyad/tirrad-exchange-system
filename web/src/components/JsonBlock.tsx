import type { JsonValue } from "@/types/api";

export function JsonBlock({ value }: { value: JsonValue | unknown }) {
  return <pre className="json-block">{JSON.stringify(value, null, 2)}</pre>;
}
