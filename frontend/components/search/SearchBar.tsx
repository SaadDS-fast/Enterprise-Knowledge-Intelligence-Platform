"use client";
import type { FormEvent } from "react";
import { useState } from "react";
import { api } from "@/lib/api";
import type { SearchResult } from "@/types";
import EvidencePanel from "./EvidencePanel";
const diagnosisCopy: Record<string, string> = {
  SUFFICIENT_EVIDENCE: "Evidence found directly",
  RETRIEVAL_FAILURE_RECOVERED: "Evidence found after an additional search",
  RETRIEVAL_FAILURE_UNRESOLVED: "Relevant evidence may exist, but the search could not verify it",
  KNOWLEDGE_ABSENT: "Information does not appear to exist in the selected documents",
  PARTIAL_EVIDENCE: "Only partial evidence found",
  CONFLICTING_EVIDENCE: "Conflicting evidence found",
  AMBIGUOUS_QUERY: "Question needs clarification",
};
const outcomeCopy: Record<string, string> = {
  ANSWER_SUPPORTED: "Answer supported",
  ANSWER_PARTIALLY_SUPPORTED: "Partially supported",
  CONFLICTING_EVIDENCE: "Conflicting evidence",
  INSUFFICIENT_EVIDENCE: "Insufficient evidence",
  KNOWLEDGE_ABSENT: "Knowledge absent",
  CLARIFICATION_REQUIRED: "Clarification required",
};
export default function SearchBar() {
  const [query,setQuery]=useState(""); const [result,setResult]=useState<SearchResult|null>(null); const [error,setError]=useState(""); const [loading,setLoading]=useState(false);
  async function submit(event:FormEvent){event.preventDefault();setLoading(true);setError("");try{setResult(await api<SearchResult>("/search",{method:"POST",body:JSON.stringify({query})}))}catch(e){setError(e instanceof Error?e.message:"Search failed")}finally{setLoading(false)}}
  const diagnosis = result?.retrieval_diagnosis;
  const outcome = result?.outcome ?? (result?.abstained ? "INSUFFICIENT_EVIDENCE" : "ANSWER_SUPPORTED");
  return <div><form className="search-form" onSubmit={submit} data-testid="search-form"><textarea value={query} onChange={e=>setQuery(e.target.value)} placeholder="Ask a question grounded in your documents..." minLength={2} required data-testid="search-query"/><button disabled={loading} data-testid="search-submit">{loading?"Searching...":"Search knowledge"}</button></form>{error&&<p className="error" data-testid="search-error">{error}</p>}{result&&<section className="result" data-testid="search-result"><div className="result-header"><h2>Answer</h2><span className={result.abstained?"warning":"success"} data-testid="search-verdict">{outcomeCopy[outcome]??outcome}</span></div><div className="diagnosis" aria-label="Answer outcome" data-testid="search-outcome"><strong>{outcomeCopy[outcome]??outcome}</strong><span>Support status: {result.support_status??(result.sufficient_evidence?"SUPPORTED":"ABSENT")} · Confidence: {result.confidence_category??"none"}</span></div>{diagnosis&&<div className="diagnosis" aria-label="Retrieval diagnosis" data-testid="retrieval-diagnosis"><strong>{diagnosisCopy[diagnosis.status]??"Retrieval diagnosis available"}</strong><span>{diagnosis.retry_performed?"Additional retrieval attempted":"Initial retrieval only"} · support score {diagnosis.final_support_score.toFixed(2)}</span></div>}<p className="answer" data-testid="search-answer">{result.answer}</p>{result.answer_value&&<p className="muted" data-testid="search-answer-value">Extracted value: {result.answer_value}</p>}{result.abstention_reason&&<p className="muted" data-testid="search-abstention-reason">Reason: {result.abstention_reason}</p>}{Boolean(result.conflicts?.length)&&<><h2>Conflicts</h2><div className="evidence-list" data-testid="search-conflicts">{result.conflicts?.map((conflict,index)=><article className="evidence" key={`${conflict.summary}-${index}`}><strong>{conflict.summary??"Conflict detected"}</strong><p>{conflict.values?.join(" / ")}</p></article>)}</div></>}<h2>Citations</h2><div className="citation-list" data-testid="search-citations">{result.citations?.length?result.citations.map((citation,index)=><article className="citation" key={`${citation.chunk_id}-${index}`}><strong>[{index+1}] {citation.document_title}</strong><p>{citation.excerpt}</p></article>):<div className="empty">No validated citations for this result.</div>}</div><h2>Evidence</h2><EvidencePanel items={result.evidence}/></section>}</div>;
}
