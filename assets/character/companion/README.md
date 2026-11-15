# Original companion atlas v1

Asset: `expressions-v1.png`, 1254x1254 RGBA with transparent background.
Generated with the built-in **image_gen** tool using the imagegen skill.
The runtime reads a 4x4 atlas non-destructively; no image model runs for animation.

Final generation prompt/specification:

> Production animation sprite atlas for an original adult feminine, gentle
> dark-fantasy companion with a calm Firekeeper-inspired mood, without copying
> a specific game character. Polished hand-painted 2D, anime-adjacent semi-realistic
> game illustration. Consistent silver-blonde softly wavy hair, visible gentle
> gray eyes, charcoal-gray modest robe, antique-gold collar, warm soft rim light.
> Real transparent background. Exact 4 columns by 4 rows, square overall sheet,
> no gutters, labels, grid lines, props, scenery or text. The same waist-up woman
> at the same scale, head and waist aligned, with head/hair/hands fully within
> each cell and a transparent safety margin. Readable expressive adult face,
> proportional anatomy and five fingers per hand.
>
> Row 1: relaxed neutral/open eyes; same neutral pose/blink; thoughtful finger
> at chin; curious head tilt. Row 2: explaining with raised index finger; same
> explanation with wrist variation/mouth slightly open; demonstrating with both
> palms open; presenting with left palm open. Row 3: playful small wave; same
> wave with wink; mildly annoyed arms crossed; mildly annoyed hand at waist.
> Row 4: shy small smile with clasped hands; same shy pose/blush/downcast eyes;
> gentle concern with hand over chest; pleasant surprise with open hands.

Frame indices are zero-based in reading order. The panel maps these poses to
emotion and intent with breathing, blink timing and gesture cycles. Atlas edges
are computed proportionally so non-divisible image dimensions do not accumulate
cropping errors.
