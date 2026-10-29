import { motion } from 'motion/react'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'

export default function MethodsDrawer({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation()
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <motion.div className="modal-backdrop" onClick={onClose}
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <motion.article className="modal" role="dialog" aria-modal="true" aria-labelledby="methods-title"
                      onClick={(e) => e.stopPropagation()}
                      initial={{ y: 24, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 16, opacity: 0 }}
                      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}>
        <button className="close" onClick={onClose} aria-label={t('methods.close')}>×</button>
        <h2 id="methods-title">{t('methods.title')}</h2>
        <p className="muted">{t('methods.intro')}</p>
        {(['forest', 'marine', 'national'] as const).map((k) => {
          const [head, ...rest] = t(`methods.${k}`).split('. ')
          return <p key={k}><strong>{head}.</strong> {rest.join('. ')}</p>
        })}
        <aside className="note">{t('methods.note')}</aside>
        <p className="muted small">{t('methods.data')}</p>
        <p className="small"><a href="https://github.com/aurvl/ncw" target="_blank" rel="noreferrer">{t('methods.repo')} ↗</a></p>
      </motion.article>
    </motion.div>
  )
}
