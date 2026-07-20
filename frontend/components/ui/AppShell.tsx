"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearSession } from "@/lib/auth";
const links = [["/dashboard","Dashboard"],["/documents","Documents"],["/search","Search"],["/research","Research"],["/evaluation","Evaluation"]];
export default function AppShell({children}:{children:React.ReactNode}) {
  const pathname=usePathname(); const router=useRouter();
  if (pathname === "/login" || pathname === "/") return <>{children}</>;
  return <div className="shell"><aside className="sidebar"><div className="brand">EKIP<span>Knowledge Intelligence</span></div><nav>{links.map(([href,label])=><Link key={href} className={pathname===href?"active":""} href={href} data-testid={`nav-${label.toLowerCase()}`}>{label}</Link>)}</nav><button className="ghost" data-testid="logout-button" onClick={()=>{clearSession();router.push("/login")}}>Sign out</button></aside><main className="main" data-testid="app-main">{children}</main></div>;
}
