"use client";

import { Badge } from "@accos/ui";
import { useEffect, useState } from "react";

import { useHealthQuery } from "../lib/api/queries";

export type NetworkState = "degraded" | "offline" | "online";

export function NetworkStatus({ state }: { state: NetworkState }) {
  if (state === "online") return null;
  const offline = state === "offline";
  return (
    <div className={`studio-network studio-network--${state}`} role={offline ? "alert" : "status"}>
      <Badge tone={offline ? "danger" : "warning"}>{offline ? "离线" : "降级"}</Badge>
      <span>
        {offline
          ? "网络连接已中断；服务器数据不会更新。"
          : "部分依赖暂不可用；最终状态将以恢复后的 API 回拉为准。"}
      </span>
    </div>
  );
}

export function ConnectedNetworkStatus() {
  const [online, setOnline] = useState(true);
  const health = useHealthQuery();

  useEffect(() => {
    setOnline(navigator.onLine);
    const markOnline = () => {
      setOnline(true);
    };
    const markOffline = () => {
      setOnline(false);
    };
    window.addEventListener("online", markOnline);
    window.addEventListener("offline", markOffline);
    return () => {
      window.removeEventListener("online", markOnline);
      window.removeEventListener("offline", markOffline);
    };
  }, []);

  if (!online) return <NetworkStatus state="offline" />;
  if (health.isError || health.data?.status === "not_ready")
    return <NetworkStatus state="degraded" />;
  return <NetworkStatus state="online" />;
}
