import StatusBadge from "@/components/ui/StatusBadge";
import type { Job } from "@/types";
export default function JobStatus({job}:{job:Job}) { return <div className="job"><StatusBadge value={job.status}/><span>{job.stage}</span>{job.error_message&&<span className="error">{job.error_message}</span>}</div>; }
