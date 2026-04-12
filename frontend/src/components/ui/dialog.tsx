import * as React from "react"
import { cn } from "@/lib/utils"
import { X } from "lucide-react"

function Dialog({
  open,
  onClose,
  children,
}: {
  open: boolean
  onClose: () => void
  children: React.ReactNode
}) {
  React.useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden"
    } else {
      document.body.style.overflow = ""
    }
    return () => {
      document.body.style.overflow = ""
    }
  }, [open])

  React.useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    if (open) window.addEventListener("keydown", handleEsc)
    return () => window.removeEventListener("keydown", handleEsc)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="fixed inset-0 bg-black/50"
        onClick={onClose}
      />
      <div className="relative z-50 mx-4 flex max-h-[90vh] w-full max-w-7xl flex-col overflow-hidden rounded-xl bg-background shadow-lg ring-1 ring-foreground/10">
        {children}
      </div>
    </div>
  )
}

function DialogHeader({
  className,
  onClose,
  ...props
}: React.ComponentProps<"div"> & { onClose?: () => void }) {
  return (
    <div
      className={cn(
        "flex items-center justify-between border-b px-6 py-4",
        className
      )}
      {...props}
    >
      <div className="flex-1">{props.children}</div>
      {onClose && (
        <button
          onClick={onClose}
          className="rounded-full p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <X className="h-5 w-5" />
        </button>
      )}
    </div>
  )
}

function DialogTitle({
  className,
  ...props
}: React.ComponentProps<"h2">) {
  return (
    <h2
      className={cn("text-lg font-semibold", className)}
      {...props}
    />
  )
}

function DialogContent({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      className={cn("flex-1 overflow-auto p-6", className)}
      {...props}
    />
  )
}

export { Dialog, DialogHeader, DialogTitle, DialogContent }
