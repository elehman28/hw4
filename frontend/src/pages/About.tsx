import { Link } from 'react-router-dom'
import Reveal from '../components/Reveal'
import { HarknessSkyline } from '../components/YaleArt'

export default function About() {
  return (
    <>
      <section className="about-hero">
        <div className="about-hero-copy">
          <p className="eyebrow">About us</p>
          <h1>Made for the people who call New Haven home</h1>
        </div>
        <HarknessSkyline className="about-art" />
      </section>

      <Reveal className="container prose-wrap">
        <div className="prose">
          <p className="lead">
            Campus Customs is a Yale merchandise shop for everyone who calls New Haven home, even if just
            for four years. We stock the layers, tees and sweatshirts that carry Bulldog spirit from the
            first day of move-in to Commencement and well beyond.
          </p>
          <h2>What we're about</h2>
          <p>
            We think school pride should feel as good as it looks. That's why we focus on comfortable,
            well-made apparel: heavyweight hoodies, soft crewnecks, easy quarter-zips, and graphic tees
            with designs for Yale athletics, the residential colleges, and The Game.
          </p>
          <h2>Who we serve</h2>
          <p>
            Students gearing up for game day, parents and grandparents who want to show where their
            Bulldog goes to school, alumni coming back for reunions, and visitors who want something to
            remember New Haven by.
          </p>
          <h2>Shop with help</h2>
          <p>
            Every product page shows live stock for each size, and our chat assistant (bottom right) can
            find styles, check your size, and point you to the right fit, even if you misspell it.
          </p>
          <Link to="/products" className="btn btn-primary">
            Shop the collection
          </Link>
        </div>
      </Reveal>
    </>
  )
}
