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
export default function SearchBar() {
  const [query,setQuery]=useState(""); const [result,setResult]=useState<SearchResult|null>(null); const [error,setError]=useState(""); const [loading,setLoading]=useState(false);
  async function submit(event:FormEvent){event.preventDefault();setLoading(true);setError("");try{setResult(await api<SearchResult>("/search",{method:"POST",body:JSON.stringify({query})}))}catch(e){setError(e instanceof Error?e.message:"Search failed")}finally{setLoading(false)}}
  const diagnosis = result?.retrieval_diagnosis;
  return <div><form className="search-form" onSubmit={submit} data-testid="search-form"><textarea value={query} onChange={e=>setQuery(e.target.value)} placeholder="Ask a question grounded in your documents..." minLength={2} required data-testid="search-query"/><button disabled={loading} data-testid="search-submit">{loading?"Searching...":"Search knowledge"}</button></form>{error&&<p className="error" data-testid="search-error">{error}</p>}{result&&<section className="result" data-testid="search-result"><div className="result-header"><h2>Answer</h2><span className={result.abstained?"warning":"success"} data-testid="search-verdict">{result.abstained?"Insufficient evidence":"Evidence verified"}</span></div>{diagnosis&&<div className="diagnosis" aria-label="Retrieval diagnosis" data-testid="retrieval-diagnosis"><strong>{diagnosisCopy[diagnosis.status]??"Retrieval diagnosis available"}</strong><span>{diagnosis.retry_performed?"Additional retrieval attempted":"Initial retrieval only"} · {Math.round(diagnosis.final_support_score*100)}% support</span></div>}<p className="answer" data-testid="search-answer">{result.answer}</p><h2>Evidence</h2><EvidencePanel items={result.evidence}/></section>}</div>;
}
