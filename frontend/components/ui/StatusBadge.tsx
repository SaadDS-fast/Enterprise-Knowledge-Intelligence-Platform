export default function StatusBadge({value}:{value:string}) { return <span className={`badge badge-${value.toLowerCase()}`}>{value}</span>; }
