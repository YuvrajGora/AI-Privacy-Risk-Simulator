import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FileText, ShieldCheck, Lock, BarChart3, ArrowRight } from 'lucide-react';

const features = [
  {
    icon: FileText,
    label: 'Text-In-Image Extraction',
    title: 'OCR Vulnerability Analysis',
    desc: 'Our AI identifies sensitive strings — PII, passwords, and location markers — hidden within images.',
    size: 'md:col-span-8',
    accent: 'text-primary',
  },
  {
    icon: ShieldCheck,
    label: 'Anonymization',
    title: 'Face Privacy Masking',
    desc: 'Automated biometric masking that preserves context while ensuring irreversible identity protection.',
    stat: '99.8% Detection Accuracy',
    size: 'md:col-span-4',
    accent: 'text-tertiary',
  },
  {
    icon: Lock,
    label: 'Hidden Vector Analysis',
    title: 'QR & Payload Integrity',
    desc: 'Scanning for malicious redirects and encoded sensitive data within pixel clusters.',
    stat: 'Real-time Heuristics',
    size: 'md:col-span-4',
    accent: 'text-secondary',
  },
  {
    icon: BarChart3,
    label: 'Instrumentation',
    title: 'EXIF Deep-Scrub',
    desc: 'Locate GPS coordinates, device serial numbers, and software signatures embedded in your files before they reach the cloud.',
    size: 'md:col-span-8',
    accent: 'text-primary',
  },
];

const steps = [
  { n: '1', title: 'Upload', desc: 'Secure drag-and-drop — supports PNG, JPG, JPEG, WEBP.' },
  { n: '2', title: 'AI Scan', desc: 'Multi-layered AI pass identifying privacy leaks.' },
  { n: '3', title: 'Risk Report', desc: 'Categorized severity score with remediation steps.' },
  { n: '4', title: 'Safe Sharing', desc: 'Export scrubbed assets ready for public distribution.' },
];

const testimonials = [
  {
    quote: 'The instrument-panel layout feels like operating a flight simulator for data privacy. The most rigorous tool we\'ve added to our security stack.',
    name: 'Dr. Elena Volkov', role: 'Lead Analyst, NexaSec',
    img: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=120&q=80',
    border: 'border-primary/40',
  },
  {
    quote: 'OCR detection is terrifyingly good. It found a Wi-Fi password reflected in a coffee cup that I didn\'t even notice was there.',
    name: 'Marcus Thorne', role: 'Privacy Architect',
    img: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=120&q=80',
    border: 'border-tertiary/40',
  },
  {
    quote: 'Essential for our field researchers. EXIF scrubbing ensures our locations remain classified during sensitive reporting.',
    name: 'Sarah J. Miller', role: 'Global Ops, Terra-X',
    img: 'https://images.unsplash.com/photo-1580489944761-15a19d654956?auto=format&fit=crop&w=120&q=80',
    border: 'border-secondary/40',
  },
];

const faqs = [
  {
    q: 'Is my data uploaded to your servers?',
    a: 'No. Analysis runs within a sandboxed environment. Images are processed ephemerally and deleted immediately after report generation.',
  },
  {
    q: 'What image formats are supported?',
    a: 'We support PNG, JPG, JPEG, and WEBP files up to 20MB.',
  },
  {
    q: 'How accurate is the AI detection?',
    a: 'Our models achieve 99.8% accuracy on face detection and 97.4% on OCR text extraction across diverse image conditions.',
  },
];

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="max-w-[1200px] mx-auto px-6 md:px-8">
      {/* ── Hero ── */}
      <section className="relative pt-16 pb-12 flex flex-col items-center text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="max-w-4xl space-y-6"
        >
          <div className="inline-flex items-center px-4 py-1 bg-primary-container/40 border border-primary/30 rounded-full text-primary text-xs font-semibold">
            <span className="mr-2 animate-pulse">●</span> AI Privacy Analysis · v2.4 Active
          </div>

          <h1 className="font-headline text-4xl md:text-6xl font-bold text-on-surface leading-tight">
            Protect Your Privacy<br />
            <span className="text-primary italic">Before</span> You Share
          </h1>

          <p className="text-on-surface-variant text-lg max-w-2xl mx-auto leading-relaxed">
            Upload any image and our AI instantly detects faces, hidden text, GPS metadata, QR codes
            and privacy leaks — so you can share confidently.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center pt-2">
            <button onClick={() => navigate('/upload')} className="btn-primary flex items-center gap-2 justify-center">
              Analyze an Image <ArrowRight className="w-4 h-4" />
            </button>
            <button onClick={() => navigate('/results')} className="btn-outline">
              View Sample Report
            </button>
          </div>

          {/* trust badges */}
          <div className="flex flex-wrap justify-center gap-6 pt-4 text-xs text-on-surface-variant">
            {['🔒 End-to-End Encrypted', '⚡ Results in &lt;3s', '🗑️ Images deleted after scan', '🆓 Free to use'].map((b, i) => (
              <span key={i} className="flex items-center gap-1" dangerouslySetInnerHTML={{ __html: b }} />
            ))}
          </div>
        </motion.div>
      </section>

      {/* ── Features Bento Grid ── */}
      <section className="py-16" id="features">
        <div className="mb-10">
          <span className="text-xs font-semibold uppercase tracking-widest text-primary">What we detect</span>
          <h2 className="font-headline text-3xl font-bold text-on-surface mt-1">Core Detection Engines</h2>
          <div className="w-12 h-1 bg-tertiary mt-2 rounded-full" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
          {features.map((f, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className={`${f.size} tonal-layer-1 border border-outline-variant/20 p-6 rounded-xl flex flex-col justify-between gap-4 hover:border-outline-variant/50 transition-colors`}
            >
              <div>
                <div className={`flex items-center gap-2 ${f.accent} mb-3`}>
                  <f.icon className="w-5 h-5" />
                  <span className="text-xs font-semibold uppercase tracking-widest">{f.label}</span>
                </div>
                <h3 className="font-headline text-xl font-bold text-on-surface mb-2">{f.title}</h3>
                <p className="text-on-surface-variant text-sm leading-relaxed">{f.desc}</p>
              </div>
              {f.stat && (
                <div className="pt-4 border-t border-outline-variant/20">
                  <span className={`text-xs font-bold uppercase tracking-widest ${f.accent}`}>{f.stat}</span>
                </div>
              )}
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Workflow Steps ── */}
      <section className="py-16">
        <div className="text-center mb-12">
          <h2 className="font-headline text-3xl font-bold text-on-surface">How It Works</h2>
          <p className="text-on-surface-variant mt-2">Four steps to full privacy confidence.</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-5">
          {steps.map((s, i) => (
            <div key={i} className="tonal-layer-1 p-6 rounded-xl space-y-4 border border-outline-variant/20">
              <div className="w-10 h-10 rounded-full bg-secondary text-on-secondary flex items-center justify-center font-bold font-headline text-lg">
                {s.n}
              </div>
              <h4 className="font-headline text-lg font-bold text-on-surface">{s.title}</h4>
              <p className="text-on-surface-variant text-sm leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Testimonials ── */}
      <section className="py-16">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {testimonials.map((t, i) => (
            <div key={i} className={`p-6 tonal-layer-1 border-l-4 ${t.border} rounded-r-xl`}>
              <p className="italic text-on-surface-variant text-sm leading-relaxed">"{t.quote}"</p>
              <div className="mt-6 flex items-center gap-4">
                <img className="w-10 h-10 rounded-full object-cover" alt={t.name} src={t.img} />
                <div>
                  <p className="text-sm font-bold text-on-surface">{t.name}</p>
                  <p className="text-xs text-outline uppercase tracking-widest">{t.role}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── FAQ ── */}
      <section className="py-16 max-w-3xl mx-auto">
        <h2 className="font-headline text-2xl font-bold text-center text-on-surface mb-10">Frequently Asked Questions</h2>
        <div className="space-y-3">
          {faqs.map((faq, i) => (
            <details key={i} className="group border border-outline-variant/20 rounded-xl overflow-hidden" open={i === 0}>
              <summary className="flex justify-between items-center p-5 bg-surface-container-low cursor-pointer hover:bg-surface-container transition-colors font-semibold text-on-surface text-sm">
                {faq.q}
                <span className="material-symbols-outlined text-xl text-outline group-open:rotate-180 transition-transform shrink-0 ml-4">expand_more</span>
              </summary>
              <div className="p-5 text-on-surface-variant bg-surface-container-low border-t border-outline-variant/20 text-sm leading-relaxed">
                {faq.a}
              </div>
            </details>
          ))}
        </div>
      </section>

      {/* ── CTA Banner ── */}
      <section className="py-16">
        <div className="tonal-layer-1 border border-outline-variant/20 rounded-2xl p-12 text-center space-y-6">
          <h2 className="font-headline text-3xl font-bold text-on-surface">Ready to Protect Your Privacy?</h2>
          <p className="text-on-surface-variant max-w-xl mx-auto">
            Upload your first image now — it takes under 3 seconds and your image is deleted immediately after.
          </p>
          <button onClick={() => navigate('/upload')} className="btn-primary inline-flex items-center gap-2">
            Start Free Analysis <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </section>
    </div>
  );
};

export default LandingPage;
