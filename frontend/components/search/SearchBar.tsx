"use client";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import type { SearchResult } from "@/types";
import EvidencePanel from "./EvidencePanel";
export default function SearchBar() {
  const [query,setQuery]=useState(""); const [result,setResult]=useState<SearchResult|null>(null); const [error,setError]=useState(""); const [loading,setLoading]=useState(false);
  async function submit(event:FormEvent){event.preventDefault();setLoading(true);setError("");try{setResult(await api<SearchResult>("/search",{method:"POST",body:JSON.stringify({query})}))}catch(e){setError(e instanceof Error?e.message:"Search failed")}finally{setLoading(false)}}
  return <div><form className="search-form" onSubmit={submit}><textarea value={query} onChange={e=>setQuery(e.target.value)} placeholder="Ask a question grounded in your documents..." minLength={2} required/><button disabled={loading}>{loading?"Searching...":"Search knowledge"}</button></form>{error&&<p className="error">{error}</p>}{result&&<section className="result"><div className="result-header"><h2>Answer</h2><span className={result.abstained?"warning":"success"}>{result.abstained?"Insufficient evidence":"Evidence verified"}</span></div><p className="answer">{result.answer}</p><h2>Evidence</h2><EvidencePanel items={result.evidence}/></section>}</div>;
}
