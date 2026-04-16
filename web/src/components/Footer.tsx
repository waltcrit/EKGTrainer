const Footer = () => (
  <footer className="border-t border-[var(--academy-line)] py-4 mt-8">
    {/* eslint-disable-next-line @next/next/no-img-element */}
    <img src="/ekg-academy-icon.png" alt="EKG Academy Icon" className="footer-icon mx-auto mb-2 h-10 w-10" />
    <p className="text-center text-xs text-[var(--academy-muted)]">
      For educational use only · Not a substitute for clinical judgment
    </p>
  </footer>
);

export default Footer;