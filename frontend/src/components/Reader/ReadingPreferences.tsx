import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export interface ReadingPreferencesValue {
  fontSize: string
  lineHeight: string
  fontFamily: "serif" | "sans-serif"
}

export const defaultReadingPreferences: ReadingPreferencesValue = {
  fontSize: "18",
  lineHeight: "1.8",
  fontFamily: "serif",
}

export function ReadingPreferences({
  value,
  onChange,
}: {
  value: ReadingPreferencesValue
  onChange: (value: ReadingPreferencesValue) => void
}) {
  return (
    <details className="rounded-lg border px-4 py-3 text-sm">
      <summary className="cursor-pointer font-medium">
        Ajustes de lectura
      </summary>
      <div className="mt-4 flex flex-wrap gap-4">
        <div className="grid gap-2">
          <Label htmlFor="reading-font-size">Tamaño de letra</Label>
          <Select
            value={value.fontSize}
            onValueChange={(fontSize) => onChange({ ...value, fontSize })}
          >
            <SelectTrigger id="reading-font-size">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[16, 18, 20, 24].map((size) => (
                <SelectItem key={size} value={String(size)}>
                  {size} px
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="reading-line-height">Interlineado</Label>
          <Select
            value={value.lineHeight}
            onValueChange={(lineHeight) => onChange({ ...value, lineHeight })}
          >
            <SelectTrigger id="reading-line-height">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {["1.5", "1.8", "2.1"].map((height) => (
                <SelectItem key={height} value={height}>
                  {height}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="reading-font-family">Tipografía</Label>
          <Select
            value={value.fontFamily}
            onValueChange={(fontFamily) => {
              if (fontFamily === "serif" || fontFamily === "sans-serif")
                onChange({ ...value, fontFamily })
            }}
          >
            <SelectTrigger id="reading-font-family">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="serif">Serif</SelectItem>
              <SelectItem value="sans-serif">Sans-serif</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </details>
  )
}
