import { useState } from "react";
import { Box } from "@mui/material";
import { proxyImageUrl } from "../api";

export function PlantImage({
  url,
  alt,
  height = 160,
  borderRadius,
}: {
  url: string | null | undefined;
  alt: string;
  height?: number | string;
  borderRadius?: number;
}) {
  const [failed, setFailed] = useState(false);
  const src = proxyImageUrl(url);

  if (!src || failed) return null;

  return (
    <Box
      component="img"
      src={src}
      alt={alt}
      onError={() => setFailed(true)}
      sx={{
        width: "100%",
        height,
        objectFit: "cover",
        display: "block",
        borderRadius: borderRadius ?? 0,
      }}
    />
  );
}
