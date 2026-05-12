"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { tokenStore } from "@/lib/api";

export default function IndexPage() {
  const router = useRouter();
  useEffect(() => {
    if (tokenStore.access) router.replace("/dashboard");
    else router.replace("/login");
  }, [router]);
  return null;
}
