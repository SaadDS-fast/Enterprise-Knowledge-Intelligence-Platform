import type { Evidence } from "@/types";
export default function EvidencePanel({items}:{items:Evidence[]}) {
  if (!items.length) return <div className="empty" data-testid="empty-evidence">No evidence was retrieved.</div>;
  return <div className="evidence-list" data-testid="evidence-list">{items.map((item,index)=><article className="evidence" key={item.chunk_id} data-testid="evidence-item"><header><strong>[{index+1}] {item.document_title}</strong><span>{Math.round(item.score*100)}%</span></header><p>{item.content}</p></article>)}</div>;
}
