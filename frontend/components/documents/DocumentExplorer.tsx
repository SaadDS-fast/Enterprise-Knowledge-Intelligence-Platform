"use client";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { DocumentItem } from "@/types";
import StatusBadge from "@/components/ui/StatusBadge";
export default function DocumentExplorer(){
 const [documents,setDocuments]=useState<DocumentItem[]>([]); const [error,setError]=useState(""); const [uploading,setUploading]=useState(false);
 const load=useCallback(async()=>{try{setDocuments(await api<DocumentItem[]>("/documents"))}catch(e){setError(e instanceof Error?e.message:"Failed to load")}},[]);
 useEffect(()=>{void load()},[load]);
 async function upload(event:FormEvent<HTMLFormElement>){event.preventDefault();const form=event.currentTarget;const input=form.elements.namedItem("file") as HTMLInputElement;if(!input.files?.[0])return;setUploading(true);setError("");const data=new FormData();data.append("file",input.files[0]);try{await api("/documents",{method:"POST",body:data});form.reset();await load();setTimeout(()=>void load(),1200)}catch(e){setError(e instanceof Error?e.message:"Upload failed")}finally{setUploading(false)}}
 return <div><form className="upload-card" onSubmit={upload}><div><h2>Upload a document</h2><p>PDF, DOCX, TXT, Markdown, HTML, CSV, or source code up to 25 MB.</p></div><input name="file" type="file" required/><button disabled={uploading}>{uploading?"Uploading...":"Upload"}</button></form>{error&&<p className="error">{error}</p>}<div className="table-card"><table><thead><tr><th>Document</th><th>Status</th><th>Created</th></tr></thead><tbody>{documents.map(doc=><tr key={doc.id}><td><strong>{doc.title}</strong><small>{doc.description}</small></td><td><StatusBadge value={doc.status}/></td><td>{new Date(doc.created_at).toLocaleString()}</td></tr>)}</tbody></table>{!documents.length&&<div className="empty">No documents uploaded yet.</div>}</div></div>;
}
