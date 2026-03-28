/**
 * NLQButton — floating action button to open/close the NLQ panel
 *
 * Props:
 *   className (string) — extra classes
 *
 * Toggles nlqOpen in useStore.
 */

import React from 'react'
import { motion } from 'framer-motion'
import { MessageCircle } from 'lucide-react'
import { useAppStore } from '@/store/appStore'

export default function NLQButton({ className = '' }) {
  const nlqOpen = useAppStore((s) => s.nlqOpen ?? false)
  const setNlqOpen = useAppStore((s) => s.setNlqOpen)

  // Hide the FAB when the panel is open — panel has its own close button
  if (nlqOpen) return null

  return (
    <motion.button
      onClick={() => setNlqOpen(true)}
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0.8, opacity: 0 }}
      whileTap={{ scale: 0.88 }}
      whileHover={{ scale: 1.08 }}
      transition={{ type: 'spring', stiffness: 400, damping: 20 }}
      aria-label="Open AI chat"
      className={[
        'fixed bottom-6 right-4 sm:bottom-8 sm:right-8 z-[60]',
        'w-12 h-12 sm:w-14 sm:h-14 rounded-full',
        'bg-primary text-white',
        'flex items-center justify-center',
        'shadow-lg shadow-primary/30',
        'focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2 focus:ring-offset-background',
        'transition-shadow duration-200',
        'hover:shadow-[0_0_28px_rgba(139,92,246,0.55)]',
        className,
      ].join(' ')}
    >
      <MessageCircle size={22} strokeWidth={2} />

      {/* Subtle pulse ring */}
      <span
        className="absolute inset-0 rounded-full bg-primary opacity-30 animate-ping"
        style={{ animationDuration: '2.4s' }}
      />
    </motion.button>
  )
}
