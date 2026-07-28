"use client";

import type { FormEvent } from "react";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { DocumentItem } from "@/types";

import StatusBadge from "@/components/ui/StatusBadge";

export default function DocumentExplorer() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [reprocessing, setReprocessing] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setDocuments(await api<DocumentItem[]>("/documents"));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const input = form.elements.namedItem("file") as HTMLInputElement;
    if (!input.files?.[0]) return;
    setUploading(true);
    setError("");
    const data = new FormData();
    data.append("file", input.files[0]);
    try {
      await api("/documents", { method: "POST", body: data });
      form.reset();
      await load();
      setTimeout(() => void load(), 1200);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function reprocess(documentId: string) {
    setReprocessing(documentId);
    setError("");
    try {
      await api(`/documents/${documentId}/reprocess`, { method: "POST" });
      await load();
      setTimeout(() => void load(), 1200);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Reprocessing failed");
    } finally {
      setReprocessing(null);
    }
  }

  return (
    <div>
      <form className="upload-card" onSubmit={upload} data-testid="document-upload-form">
        <div>
          <h2>Upload a document</h2>
          <p>PDF, DOCX, TXT, Markdown, HTML, CSV, or source code up to 25 MB.</p>
        </div>
        <label className="sr-only" htmlFor="document-file">
          Document file
        </label>
        <input id="document-file" name="file" type="file" required data-testid="document-file-input" />
        <button disabled={uploading} data-testid="document-upload-submit">
          {uploading ? "Uploading..." : "Upload"}
        </button>
      </form>
      {error ? <p className="error">{error}</p> : null}
      <div className="table-card">
        <table>
          <thead>
            <tr>
              <th>Document</th>
              <th>Status</th>
              <th>Extraction</th>
              <th>Pages / chunks</th>
              <th>Pipeline</th>
              <th>Created</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr key={doc.id} data-testid="document-row">
                <td>
                  <strong>{doc.title}</strong>
                  <small>{doc.filename ?? doc.description}</small>
                </td>
                <td>
                  <span data-testid="document-status">
                    <StatusBadge value={doc.status} />
                  </span>
                </td>
                <td>
                  <StatusBadge value={doc.extraction_quality ?? "pending"} />
                  {doc.status === "requires_ocr" ? <small>OCR is required before search.</small> : null}
                </td>
                <td>{doc.page_count ?? "—"} / {doc.chunk_count ?? 0}</td>
                <td>
                  <small>{doc.pipeline_version?.chunking_version ?? "legacy"}</small>
                  {doc.reprocessing_recommended ? <small>Update recommended</small> : null}
                </td>
                <td>{new Date(doc.created_at).toLocaleString()}</td>
                <td>
                  <button
                    type="button"
                    disabled={reprocessing === doc.id || doc.status === "processing"}
                    onClick={() => void reprocess(doc.id)}
                    aria-label={`Reprocess ${doc.title}`}
                  >
                    {reprocessing === doc.id ? "Starting…" : "Reprocess"}
                  </button>
                  {doc.error_category ? <small>{doc.error_category}</small> : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!documents.length ? <div className="empty">No documents uploaded yet.</div> : null}
      </div>
    </div>
  );
}
