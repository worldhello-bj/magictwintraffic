import { decodePayload } from "./protocol";
self.onmessage = async (
  event: MessageEvent<{
    id: number;
    buffer: ArrayBuffer;
    records: number;
    compression?: string;
  }>,
) => {
  try {
    const frames = await decodePayload(
      event.data.buffer,
      event.data.records,
      event.data.compression,
    );
    self.postMessage({ id: event.data.id, frames });
  } catch (e) {
    self.postMessage({ id: event.data.id, error: String(e) });
  }
};
