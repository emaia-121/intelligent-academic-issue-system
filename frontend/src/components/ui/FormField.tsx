import {
  useState,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from 'react'
import { Eye, EyeOff } from 'lucide-react'
import clsx from 'clsx'

const BASE_INPUT =
  'h-11 w-full rounded-lg border border-slate-200 bg-white px-3.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50 disabled:text-slate-400'

function FieldWrapper({
  label,
  htmlFor,
  error,
  hint,
  required,
  children,
}: {
  label: string
  htmlFor: string
  error?: string
  hint?: string
  required?: boolean
  children: ReactNode
}) {
  return (
    <div>
      <label htmlFor={htmlFor} className="mb-1.5 block text-sm font-medium text-slate-700">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      {children}
      {error ? (
        <p className="mt-1.5 text-xs font-medium text-red-600">{error}</p>
      ) : hint ? (
        <p className="mt-1.5 text-xs text-slate-400">{hint}</p>
      ) : null}
    </div>
  )
}

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
  hint?: string
}

export function TextField({ label, error, hint, id, required, className, ...rest }: TextFieldProps) {
  const inputId = id ?? `field-${label.replace(/\s+/g, '-').toLowerCase()}`
  return (
    <FieldWrapper label={label} htmlFor={inputId} error={error} hint={hint} required={required}>
      <input
        id={inputId}
        required={required}
        className={clsx(BASE_INPUT, error && 'border-red-300 focus:border-red-400 focus:ring-red-100', className)}
        {...rest}
      />
    </FieldWrapper>
  )
}

export function PasswordField({ label, error, hint, id, required, className, ...rest }: TextFieldProps) {
  const [visible, setVisible] = useState(false)
  const inputId = id ?? `field-${label.replace(/\s+/g, '-').toLowerCase()}`
  return (
    <FieldWrapper label={label} htmlFor={inputId} error={error} hint={hint} required={required}>
      <div className="relative">
        <input
          id={inputId}
          type={visible ? 'text' : 'password'}
          required={required}
          className={clsx(
            BASE_INPUT,
            'pr-10',
            error && 'border-red-300 focus:border-red-400 focus:ring-red-100',
            className,
          )}
          {...rest}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
          tabIndex={-1}
          aria-label={visible ? 'Hide password' : 'Show password'}
        >
          {visible ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
        </button>
      </div>
    </FieldWrapper>
  )
}

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string
  error?: string
  hint?: string
  options: { value: string; label: string }[]
  placeholder?: string
}

export function SelectField({
  label,
  error,
  hint,
  id,
  required,
  className,
  options,
  placeholder,
  ...rest
}: SelectFieldProps) {
  const inputId = id ?? `field-${label.replace(/\s+/g, '-').toLowerCase()}`
  return (
    <FieldWrapper label={label} htmlFor={inputId} error={error} hint={hint} required={required}>
      <select
        id={inputId}
        required={required}
        className={clsx(BASE_INPUT, error && 'border-red-300 focus:border-red-400 focus:ring-red-100', className)}
        {...rest}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </FieldWrapper>
  )
}

interface TextAreaFieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string
  error?: string
  hint?: string
}

export function TextAreaField({ label, error, hint, id, required, className, ...rest }: TextAreaFieldProps) {
  const inputId = id ?? `field-${label.replace(/\s+/g, '-').toLowerCase()}`
  return (
    <FieldWrapper label={label} htmlFor={inputId} error={error} hint={hint} required={required}>
      <textarea
        id={inputId}
        required={required}
        className={clsx(
          BASE_INPUT,
          'h-auto min-h-[110px] resize-y py-2.5',
          error && 'border-red-300 focus:border-red-400 focus:ring-red-100',
          className,
        )}
        {...rest}
      />
    </FieldWrapper>
  )
}
