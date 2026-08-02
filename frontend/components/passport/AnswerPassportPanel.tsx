"use client";

import { useEffect, useRef, useState } from "react";

import {
  abbreviateIdentifier,
  downloadTransient,
  getCurrentTrustBundle,
  getPassportExport,
  getPassportMetadata,
  presentPassportStatus,
  safePassportFilename,
  safePassportMessage,
  type PassportMetadata,
} from "@/lib/passport";

type Props = {
  reference: {
    passport_id: string;
    schema_version: string;
    metadata_available: boolean;
    export_available: boolean;
  };
};

const TRUST_WARNING =
  "Obtaining the passport and trust bundle from the same service does not by itself establish initial trust. The trust anchor must be authenticated through an independently trusted channel.";

function formatDate(value: string | null): string {
  if (!value) return "Not specified";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? "Unavailable" : date.toLocaleString();
}

export default function AnswerPassportPanel({ reference }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [metadata, setMetadata] = useState<PassportMetadata | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [message, setMessage] = useState("");
  const controllers = useRef(new Set<AbortController>());
  const objectUrlCleanups = useRef(new Set<() => void>());

  useEffect(() => {
    const activeControllers = controllers.current;
    const activeCleanups = objectUrlCleanups.current;
    return () => {
      activeControllers.forEach((controller) => controller.abort());
      activeControllers.clear();
      activeCleanups.forEach((cleanup) => cleanup());
      activeCleanups.clear();
    };
  }, []);

  function beginRequest(): AbortController {
    const controller = new AbortController();
    controllers.current.add(controller);
    return controller;
  }

  function endRequest(controller: AbortController): void {
    controllers.current.delete(controller);
  }

  function trackObjectUrl(cleanup: () => void): void {
    objectUrlCleanups.current.add(cleanup);
    window.setTimeout(() => objectUrlCleanups.current.delete(cleanup), 0);
  }

  async function loadMetadata() {
    if (!reference.metadata_available || loading) return;
    setLoading(true);
    setMetadata(null);
    setMessage("");
    const controller = beginRequest();
    try {
      setMetadata(await getPassportMetadata(reference.passport_id, controller.signal));
    } catch (error) {
      if (!controller.signal.aborted) setMessage(safePassportMessage(error));
    } finally {
      endRequest(controller);
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  async function toggleDetails() {
    if (expanded) {
      setExpanded(false);
      return;
    }
    setExpanded(true);
    if (metadata || !reference.metadata_available) return;
    await loadMetadata();
  }

  async function exportPassport() {
    setDownloading(true);
    setMessage("");
    const controller = beginRequest();
    try {
      const blob = await getPassportExport(reference.passport_id, controller.signal);
      const cleanup = downloadTransient(blob, safePassportFilename(reference.passport_id));
      trackObjectUrl(cleanup);
      setMessage("Passport export downloaded.");
    } catch (error) {
      if (!controller.signal.aborted) setMessage(safePassportMessage(error));
    } finally {
      endRequest(controller);
      if (!controller.signal.aborted) setDownloading(false);
    }
  }

  async function downloadTrustBundle() {
    setDownloading(true);
    setMessage("");
    const controller = beginRequest();
    try {
      const trust = await getCurrentTrustBundle(controller.signal);
      const blob = new Blob([trust.verifier_bundle], { type: "application/json" });
      const cleanup = downloadTransient(blob, "answer-passport-trust-bundle.json");
      trackObjectUrl(cleanup);
      setMessage("Public verification trust bundle downloaded.");
    } catch (error) {
      if (!controller.signal.aborted) setMessage(safePassportMessage(error));
    } finally {
      endRequest(controller);
      if (!controller.signal.aborted) setDownloading(false);
    }
  }

  const presentation = metadata ? presentPassportStatus(metadata.status) : null;
  const exportAllowed = Boolean(metadata?.export_available ?? reference.export_available);

  return (
    <aside className="passport-card" aria-labelledby="passport-title" data-testid="passport-card">
      <div className="passport-heading">
        <div>
          <strong id="passport-title">Answer Passport</strong>
          <span>A signed verification record is available for this supported answer.</span>
        </div>
        <button
          type="button"
          className="ghost"
          aria-expanded={expanded}
          aria-controls="passport-details"
          onClick={toggleDetails}
        >
          {expanded ? "Hide assurance details" : "View assurance details"}
        </button>
      </div>

      {expanded ? (
        <div id="passport-details" className="passport-details">
          {loading ? <p role="status">Loading verification metadata…</p> : null}
          {!reference.metadata_available && !loading ? (
            <p className="muted">Verification metadata is currently unavailable.</p>
          ) : null}
          {metadata ? (
            <>
              <h3>Assurance status</h3>
              <dl className="passport-status-grid">
                <div>
                  <dt>Artifact integrity</dt>
                  <dd>{metadata.artifact_integrity}</dd>
                </div>
                <div>
                  <dt>Passport freshness</dt>
                  <dd>{metadata.freshness.replaceAll("_", " ")}</dd>
                </div>
                <div>
                  <dt>Signing-key lifecycle</dt>
                  <dd>{metadata.key_lifecycle_status.replaceAll("_", " ")}</dd>
                </div>
                <div>
                  <dt>Trust availability</dt>
                  <dd className={`passport-${presentation?.tone}`}>{presentation?.label}</dd>
                </div>
                <div>
                  <dt>Export policy</dt>
                  <dd>{exportAllowed ? "Authorized for this session" : "Not available"}</dd>
                </div>
              </dl>
              {presentation?.blocking ? (
                <p className="error" role="alert">
                  This record cannot be treated as verified.
                </p>
              ) : null}
              <h3>Record metadata</h3>
              <dl className="passport-metadata">
                <div><dt>Passport ID</dt><dd className="wrap">{metadata.passport_id}</dd></div>
                <div><dt>Schema</dt><dd>{metadata.schema_version}</dd></div>
                <div><dt>Issued</dt><dd>{formatDate(metadata.issued_at)}</dd></div>
                <div><dt>Expires</dt><dd>{formatDate(metadata.expires_at)}</dd></div>
                <div><dt>Signer key</dt><dd>{abbreviateIdentifier(metadata.signer_key_id)}</dd></div>
              </dl>
              <div className="passport-actions">
                {exportAllowed ? (
                  <button type="button" onClick={exportPassport} disabled={downloading || presentation?.blocking}>
                    {metadata.status === "KEY_REVOKED" ? "Download forensic export" : "Download passport ZIP"}
                  </button>
                ) : (
                  <span className="muted">Your current role cannot export this record.</span>
                )}
                <button type="button" className="ghost" onClick={downloadTrustBundle} disabled={downloading}>
                  Download public verification trust bundle
                </button>
                <button type="button" className="ghost" onClick={loadMetadata} disabled={loading || downloading}>
                  Refresh assurance status
                </button>
              </div>
            </>
          ) : null}

          <section className="offline-guide" aria-labelledby="offline-title">
            <h3 id="offline-title">Verify offline</h3>
            <p>
              The ZIP contains <code>passport.json</code>, <code>passport.sig</code>,
              <code> export-manifest.json</code>, and possibly <code>trust-bundle.json</code>.
              Verification requires no LLM or document retrieval and does not re-answer the question.
            </p>
            <pre><code>{`ekip-vap verify passport.json passport.sig \\\n  --trust-bundle trust-bundle.json`}</code></pre>
            <pre><code>{`python -m app.passport.cli verify \\\n  passport.json passport.sig \\\n  --trust-bundle trust-bundle.json`}</code></pre>
            <p>
              Exit 0 means VERIFIED. Exit 2 means review required, including
              VERIFIED_WITHOUT_SNAPSHOT, STALE, EXPIRED, or INDETERMINATE. Exit 1 means invalid,
              revoked, modified, unknown-key, malformed, or trust failure.
            </p>
            <p>Signature validity is separate from current factual validity. Stale, expired, and revoked records require policy review.</p>
            <p className="warning">{TRUST_WARNING}</p>
          </section>
        </div>
      ) : null}
      {message ? <p className="passport-message" role="status">{message}</p> : null}
    </aside>
  );
}
