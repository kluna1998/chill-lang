import { Link } from "@tanstack/react-router"

import { cn } from "@/lib/utils"

interface LogoProps {
  variant?: "full" | "icon" | "responsive"
  className?: string
  asLink?: boolean
}

export function Logo({
  variant = "full",
  className,
  asLink = true,
}: LogoProps) {
  const content = (
    <span
      className={cn(
        "inline-flex items-center text-xl font-semibold",
        className,
      )}
    >
      <span
        className={cn(
          variant === "responsive" && "group-data-[collapsible=icon]:hidden",
        )}
      >
        {variant === "icon" ? "CL" : "Chill-Lang"}
      </span>
      {variant === "responsive" && (
        <span
          aria-hidden="true"
          className="hidden group-data-[collapsible=icon]:inline"
        >
          CL
        </span>
      )}
    </span>
  )

  if (!asLink) return content

  return (
    <Link to="/" aria-label="Chill-Lang">
      {content}
    </Link>
  )
}
