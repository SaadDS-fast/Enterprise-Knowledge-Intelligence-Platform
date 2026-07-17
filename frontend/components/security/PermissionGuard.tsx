"use client";
import { isAuthenticated } from "@/lib/auth";
export default function PermissionGuard({children,fallback=null}:{children:React.ReactNode;fallback?:React.ReactNode}) { return isAuthenticated()?<>{children}</>:<>{fallback}</>; }
