"use client";

import { Suspense } from "react";

import Link from "next/link";

import {
  FormEvent,
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";

import {
  api,
} from "@/lib/api";

import {
  workspaceForRole,
} from "@/lib/workspace";


const MARKET_VIDEO =
  "https://videos.pexels.com/video-files/35827781/15191684_3840_2160_30fps.mp4";

const MARKET_POSTER =
  "https://images.pexels.com/videos/35827781/african-market-west-africa-35827781.jpeg?auto=compress&dpr=1&h=750&w=1260";


function BrandMark({
  compact = false,
}: {
  compact?: boolean;
}) {
  return (
    <div
      className={
        compact
          ? "brand brandCompact"
          : "brand"
      }
    >
      <div className="brandIcon">
        <span>S</span>
        <span>D</span>
      </div>

      <div className="brandText">
        <strong>StoreDash</strong>

        {!compact && (
          <span>
            Commerce in motion
          </span>
        )}
      </div>
    </div>
  );
}


function AmbientVideo({
  className,
  delay,
}: {
  className: string;
  delay: number;
}) {
  return (
    <div
      className={`ambientVideo ${className}`}
      style={{
        animationDelay:
          `${delay}s`,
      }}
      aria-hidden="true"
    >
      <video
        autoPlay
        loop
        muted
        playsInline
        preload="metadata"
        poster={MARKET_POSTER}
      >
        <source
          src={MARKET_VIDEO}
          type="video/mp4"
        />
      </video>

      <div className="ambientShade" />
    </div>
  );
}


function LoginPageContent() {
  const router = useRouter();

  const [
    email,
    setEmail,
  ] = useState("");

  const [
    password,
    setPassword,
  ] = useState("");

  const [
    error,
    setError,
  ] = useState("");

  const [
    loading,
    setLoading,
  ] = useState(false);


  async function submit(
    event: FormEvent
  ) {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      await api(
        "/auth/login",
        {
          method: "POST",

          body: JSON.stringify({
            email,
            password,
          }),
        }
      );

      const user = await api<{
        role: string;
      }>("/auth/me");

      router.replace(
        workspaceForRole(user.role)
      );

      router.refresh();

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Login failed."
      );
    } finally {
      setLoading(false);
    }
  }


  return (
    <main className="loginPage">
      <div
        className="backgroundMedia"
        aria-hidden="true"
      >
        <video
          autoPlay
          loop
          muted
          playsInline
          preload="metadata"
          poster={MARKET_POSTER}
        >
          <source
            src={MARKET_VIDEO}
            type="video/mp4"
          />
        </video>

        <div className="backgroundWash" />
        <div className="backgroundGrid" />
      </div>

      <div
        className="brandWatermark"
        aria-hidden="true"
      >
        STOREDASH
      </div>

      <AmbientVideo
        className="videoOne"
        delay={0}
      />

      <AmbientVideo
        className="videoTwo"
        delay={-4}
      />

      <section className="storyPanel">
        <BrandMark />

        <div className="storyCopy">
          <div className="eyebrow">
            Built for the market.
            Built to move.
          </div>

          <h1>
            From the supplier
            <br />
            to the shop,
            <br />
            <em>without the chaos.</em>
          </h1>

          <p>
            One operating system for
            sourcing, delivery, payments,
            and the people moving goods
            every day.
          </p>

          <div className="flow">
            <span>Source</span>
            <i />
            <span>Move</span>
            <i />
            <span>Deliver</span>
          </div>
        </div>

        <div className="storyFooter">
          <span className="statusDot" />
          StoreDash Operations
        </div>
      </section>

      <section className="loginShell">
        <div className="mobileBrand">
          <BrandMark compact />
        </div>

        <form
          onSubmit={submit}
          className="loginCard"
        >
          <div className="cardHeader">
            <span className="cardKicker">
              Employee access
            </span>

            <h2>
              Welcome back.
            </h2>

            <p>
              Sign in to continue to
              StoreDash operations.
            </p>
          </div>

          <label className="field">
            <span>Email</span>

            <input
              type="email"
              required
              autoComplete="email"
              placeholder="you@storedash.com"
              value={email}
              onChange={(event) =>
                setEmail(
                  event.target.value
                )
              }
            />
          </label>

          <label className="field">
            <span>Password</span>

            <input
              type="password"
              required
              autoComplete="current-password"
              placeholder="Enter your password"
              value={password}
              onChange={(event) =>
                setPassword(
                  event.target.value
                )
              }
            />
          </label>

          {error && (
            <div
              className="error"
              role="alert"
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="loginButton"
          >
            <span>
              {loading
                ? "Logging in..."
                : "Enter StoreDash"}
            </span>

            <span
              className="arrow"
              aria-hidden="true"
            >
              →
            </span>
          </button>

          <div className="cardDivider">
            <span />
            <small>
              secure employee access
            </small>
            <span />
          </div>

          <p className="signupLink">
            First time here?{" "}

            <Link href="/signup">
              Create employee account
            </Link>
          </p>
        </form>

        <p className="securityNote">
          Protected StoreDash workspace
          · Authorized employees only
        </p>
      </section>

      <style jsx>{`
        .loginPage {
          position: relative;
          isolation: isolate;
          min-height: 100svh;
          overflow: hidden;
          display: grid;
          grid-template-columns:
            minmax(0, 1.2fr)
            minmax(390px, .8fr);
          color: #fff;
          background: #0d1621;
        }

        .backgroundMedia {
          position: absolute;
          inset: 0;
          z-index: -5;
          overflow: hidden;
          background-image:
            url("${MARKET_POSTER}");
          background-size: cover;
          background-position: center;
        }

        .backgroundMedia video {
          width: 100%;
          height: 100%;
          object-fit: cover;
          transform: scale(1.04);
          filter:
            saturate(.82)
            contrast(1.04)
            brightness(.72);
        }

        .backgroundWash {
          position: absolute;
          inset: 0;
          background:
            linear-gradient(
              90deg,
              rgba(5, 13, 23, .92) 0%,
              rgba(5, 13, 23, .79) 42%,
              rgba(5, 13, 23, .52) 66%,
              rgba(5, 13, 23, .72) 100%
            ),
            linear-gradient(
              180deg,
              rgba(5, 13, 23, .12),
              rgba(5, 13, 23, .56)
            );
        }

        .backgroundGrid {
          position: absolute;
          inset: 0;
          opacity: .12;
          background-image:
            linear-gradient(
              rgba(255,255,255,.14) 1px,
              transparent 1px
            ),
            linear-gradient(
              90deg,
              rgba(255,255,255,.14) 1px,
              transparent 1px
            );
          background-size:
            72px 72px;
          mask-image:
            linear-gradient(
              90deg,
              #000,
              transparent 75%
            );
        }

        .brandWatermark {
          position: absolute;
          left: -1.6vw;
          bottom: -3.4vw;
          z-index: -1;
          font-size:
            clamp(72px, 12vw, 190px);
          line-height: .8;
          font-weight: 900;
          letter-spacing: -.075em;
          color:
            rgba(255,255,255,.038);
          user-select: none;
          pointer-events: none;
          white-space: nowrap;
        }

        .storyPanel {
          min-width: 0;
          min-height: 100svh;
          padding:
            clamp(30px, 4.2vw, 68px);
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          position: relative;
          z-index: 3;
        }

        .brand {
          display: inline-flex;
          align-items: center;
          gap: 13px;
          width: fit-content;
        }

        .brandIcon {
          width: 48px;
          height: 48px;
          border-radius: 15px;
          display: grid;
          place-items: center;
          position: relative;
          overflow: hidden;
          color: white;
          background:
            linear-gradient(
              135deg,
              #ff2b37,
              #fa5b31
            );
          box-shadow:
            0 14px 34px
            rgba(255,43,55,.28);
          font-weight: 900;
          letter-spacing: -.1em;
        }

        .brandIcon::after {
          content: "";
          position: absolute;
          inset: 1px;
          border-radius: 14px;
          border:
            1px solid
            rgba(255,255,255,.27);
        }

        .brandIcon span {
          position: absolute;
          font-size: 17px;
        }

        .brandIcon span:first-child {
          transform:
            translate(-5px, -4px);
        }

        .brandIcon span:last-child {
          transform:
            translate(6px, 6px);
          opacity: .72;
        }

        .brandText {
          display: grid;
          gap: 2px;
        }

        .brandText strong {
          font-size: 21px;
          letter-spacing: -.035em;
        }

        .brandText span {
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: .2em;
          color:
            rgba(255,255,255,.58);
        }

        .storyCopy {
          max-width: 680px;
          margin:
            clamp(70px, 10vh, 120px)
            0
            auto;
        }

        .eyebrow {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 8px 12px;
          border:
            1px solid
            rgba(255,255,255,.16);
          border-radius: 999px;
          background:
            rgba(255,255,255,.07);
          backdrop-filter: blur(18px);
          -webkit-backdrop-filter:
            blur(18px);
          color:
            rgba(255,255,255,.82);
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: .16em;
          font-weight: 700;
        }

        .storyCopy h1 {
          margin:
            24px 0 18px;
          max-width: 670px;
          font-size:
            clamp(52px, 6vw, 92px);
          line-height: .92;
          letter-spacing: -.065em;
          font-weight: 830;
          text-wrap: balance;
        }

        .storyCopy h1 em {
          font-style: normal;
          color: #ff5a61;
        }

        .storyCopy p {
          max-width: 570px;
          margin: 0;
          font-size:
            clamp(16px, 1.5vw, 20px);
          line-height: 1.65;
          color:
            rgba(255,255,255,.7);
        }

        .flow {
          margin-top: 34px;
          display: flex;
          align-items: center;
          gap: 13px;
          width: fit-content;
          color:
            rgba(255,255,255,.82);
          font-size: 12px;
          font-weight: 750;
          letter-spacing: .13em;
          text-transform: uppercase;
        }

        .flow i {
          width: 32px;
          height: 1px;
          background:
            rgba(255,255,255,.28);
          position: relative;
        }

        .flow i::after {
          content: "";
          position: absolute;
          right: -1px;
          top: -2px;
          width: 5px;
          height: 5px;
          border-top:
            1px solid
            rgba(255,255,255,.45);
          border-right:
            1px solid
            rgba(255,255,255,.45);
          transform: rotate(45deg);
        }

        .storyFooter {
          display: flex;
          align-items: center;
          gap: 9px;
          color:
            rgba(255,255,255,.54);
          font-size: 12px;
          letter-spacing: .11em;
          text-transform: uppercase;
        }

        .statusDot {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          background: #37d991;
          box-shadow:
            0 0 0 5px
            rgba(55,217,145,.12);
        }

        .loginShell {
          min-height: 100svh;
          padding:
            clamp(22px, 4vw, 58px);
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          position: relative;
          z-index: 6;
        }

        .loginCard {
          width: 100%;
          max-width: 445px;
          display: grid;
          gap: 18px;
          padding:
            clamp(27px, 3vw, 40px);
          border:
            1px solid
            rgba(255,255,255,.42);
          border-radius: 28px;
          background:
            rgba(249,251,255,.91);
          box-shadow:
            0 32px 90px
            rgba(0,0,0,.34);
          backdrop-filter:
            blur(28px)
            saturate(1.18);
          -webkit-backdrop-filter:
            blur(28px)
            saturate(1.18);
          color: #121b2c;
        }

        .cardHeader {
          margin-bottom: 5px;
        }

        .cardKicker {
          display: block;
          margin-bottom: 10px;
          color: #f03b46;
          font-size: 11px;
          font-weight: 800;
          letter-spacing: .16em;
          text-transform: uppercase;
        }

        .cardHeader h2 {
          margin: 0;
          font-size:
            clamp(31px, 3vw, 39px);
          line-height: 1;
          letter-spacing: -.052em;
        }

        .cardHeader p {
          margin: 11px 0 0;
          color: #667085;
          font-size: 14px;
          line-height: 1.55;
        }

        .field {
          display: grid;
          gap: 8px;
          color: #283348;
          font-size: 13px;
          font-weight: 750;
        }

        .field input {
          width: 100%;
          height: 51px;
          padding: 0 15px;
          border:
            1px solid
            #d9dfe8;
          border-radius: 13px;
          outline: none;
          background:
            rgba(255,255,255,.86);
          color: #111a2a;
          font-size: 15px;
          transition:
            border-color .18s ease,
            box-shadow .18s ease,
            transform .18s ease;
        }

        .field input::placeholder {
          color: #a1a9b7;
        }

        .field input:focus {
          border-color: #ff5963;
          box-shadow:
            0 0 0 4px
            rgba(255,43,55,.1);
          transform:
            translateY(-1px);
        }

        .error {
          border:
            1px solid #ffcdd1;
          border-radius: 12px;
          padding: 11px 13px;
          background: #fff1f2;
          color: #ad1d27;
          font-size: 13px;
          line-height: 1.45;
        }

        .loginButton {
          height: 54px;
          margin-top: 3px;
          border: 0;
          border-radius: 14px;
          padding: 0 17px 0 19px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          cursor: pointer;
          color: white;
          background:
            linear-gradient(
              135deg,
              #111a2c,
              #1c2a44
            );
          box-shadow:
            0 14px 32px
            rgba(17,26,44,.18);
          font-size: 14px;
          font-weight: 750;
          transition:
            transform .18s ease,
            box-shadow .18s ease,
            opacity .18s ease;
        }

        .loginButton:hover:not(:disabled) {
          transform:
            translateY(-2px);
          box-shadow:
            0 17px 36px
            rgba(17,26,44,.24);
        }

        .loginButton:disabled {
          cursor: wait;
          opacity: .68;
        }

        .arrow {
          width: 28px;
          height: 28px;
          border-radius: 50%;
          display: grid;
          place-items: center;
          background:
            rgba(255,255,255,.11);
          font-size: 17px;
        }

        .cardDivider {
          display: grid;
          grid-template-columns:
            1fr auto 1fr;
          align-items: center;
          gap: 10px;
          margin-top: 1px;
        }

        .cardDivider span {
          height: 1px;
          background: #e1e5ec;
        }

        .cardDivider small {
          color: #9ba3b0;
          font-size: 10px;
          letter-spacing: .08em;
          text-transform: uppercase;
          white-space: nowrap;
        }

        .signupLink {
          margin: 0;
          text-align: center;
          color: #7a8495;
          font-size: 13px;
        }

        .signupLink a {
          color: #202a3c;
          font-weight: 800;
        }

        .securityNote {
          margin: 18px 0 0;
          color:
            rgba(255,255,255,.48);
          font-size: 10px;
          text-transform: uppercase;
          letter-spacing: .13em;
          text-align: center;
        }

        .mobileBrand {
          display: none;
        }

        .ambientVideo {
          position: absolute;
          z-index: 1;
          overflow: hidden;
          border:
            1px solid
            rgba(255,255,255,.18);
          box-shadow:
            0 24px 60px
            rgba(0,0,0,.28);
          pointer-events: none;
          animation:
            drift 10s ease-in-out
            infinite alternate;
        }

        .ambientVideo video {
          width: 100%;
          height: 100%;
          object-fit: cover;
          filter:
            saturate(.85)
            brightness(.86);
        }

        .ambientShade {
          position: absolute;
          inset: 0;
          background:
            linear-gradient(
              140deg,
              rgba(255,255,255,.08),
              rgba(4,11,18,.12)
            );
        }

        .videoOne {
          width:
            clamp(160px, 16vw, 250px);
          aspect-ratio: 4 / 5;
          right:
            clamp(350px, 31vw, 520px);
          top: 7vh;
          border-radius: 30px;
          transform:
            rotate(5deg);
          opacity: .58;
        }

        .videoOne video {
          object-position: 22% center;
        }

        .videoTwo {
          width:
            clamp(180px, 19vw, 290px);
          aspect-ratio: 16 / 10;
          right:
            clamp(330px, 29vw, 490px);
          bottom: 7vh;
          border-radius: 26px;
          transform:
            rotate(-5deg);
          opacity: .46;
        }

        .videoTwo video {
          object-position: 78% center;
        }

        @keyframes drift {
          0% {
            translate: 0 -5px;
          }

          50% {
            translate: 7px 7px;
          }

          100% {
            translate: -4px 13px;
          }
        }

        @media (
          max-width: 1050px
        ) {
          .loginPage {
            grid-template-columns:
              minmax(0, 1fr)
              minmax(370px, .9fr);
          }

          .storyCopy h1 {
            font-size:
              clamp(46px, 6vw, 68px);
          }

          .ambientVideo {
            display: none;
          }
        }

        @media (
          max-width: 820px
        ) {
          .loginPage {
            display: block;
          }

          .storyPanel {
            display: none;
          }

          .backgroundWash {
            background:
              linear-gradient(
                180deg,
                rgba(4,11,18,.63),
                rgba(4,11,18,.82)
              );
          }

          .loginShell {
            padding:
              22px 18px 28px;
          }

          .mobileBrand {
            display: block;
            width: 100%;
            max-width: 445px;
            margin-bottom: 20px;
          }

          .brandCompact
            :global(.brandIcon) {
            width: 42px;
            height: 42px;
            border-radius: 13px;
          }

          .loginCard {
            border-radius: 24px;
            background:
              rgba(250,251,253,.94);
          }

          .brandWatermark {
            font-size: 26vw;
            left: -4vw;
            bottom: 1vh;
          }
        }

        @media (
          max-width: 480px
        ) {
          .loginShell {
            justify-content:
              flex-start;
            padding-top: 28px;
          }

          .loginCard {
            margin-top: auto;
            margin-bottom: auto;
          }

          .cardHeader h2 {
            font-size: 33px;
          }
        }

        @media (
          prefers-reduced-motion:
            reduce
        ) {
          .backgroundMedia video,
          .ambientVideo video {
            display: none;
          }

          .ambientVideo {
            animation: none;
          }
        }
      `}</style>
    </main>
  );
}


export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div
          style={{
            minHeight: "100vh",
            display: "grid",
            placeItems: "center",
            background: "#0d1621",
            color: "#fff",
          }}
        >
          Loading StoreDash...
        </div>
      }
    >
      <LoginPageContent />
    </Suspense>
  );
}
