## Part D — Weather API report

### Scope, provenance and data flow

This project converts a location name into a daily forecast using direct HTTP rather than a weather wrapper. Configuration holds the city, actual contact email, candidate index, forecast length and live/offline switch. Offline mode is the default so another student or marker can execute everything without a network connection or somebody else's contact details. Supplied JSON fixtures are hand-authored synthetic examples, not downloaded forecasts. Their displayed values demonstrate software behaviour and must not be interpreted as actual Kampala weather. Live mode is explicit and never silently substitutes fixtures after failure.

```text
Location + contact + configured candidate index
                    |
                    v
          Geocoding HTTP / fixture
                    |
                    v
        Validate and display candidates
                    |
                    v
        Explicit configured selection
                    |
            latitude + longitude
              /              \
             v                v
    Open-Meteo daily      MET UTC samples
             |                |
       validate JSON     validate JSON
             |                |
        DataFrame        point DataFrame
             |                |
         table/chart + qualified comparison
```

A geocoder can omit the results key when nothing matches. Parsing returns an empty list for that case; choosing from it raises an actionable error instead of indexing a missing result. For ambiguous names such as Springfield, candidate administrative areas and countries are displayed. Users choose a zero-based index in the configuration, inspect the table and rerun if necessary. This reconciles explicit selection with the requirement that Restart & Run All must not block on interactive input. The first returned result cannot automatically be assumed to be the intended place.

### HTTP fundamentals and interpretation

Part A makes equivalent geocoding requests with urllib and requests. urllib needs explicit URL construction using urlencode, a Request carrying headers, and JSON decoding of response bytes. requests uses params for encoding and offers response.json and raise_for_status. Both implementations identify the application and set bounded timeouts. urllib raises HTTPError for unsuccessful status codes; it has no raise_for_status method. This unavoidable library distinction is documented. In live mode, the notebook prints measured status, Content-Type and wall-clock response time. Offline execution does not fabricate network measurements.

The forecast request explicitly asks for daily temperature minimum and maximum, precipitation sum, maximum wind and weather code. It sets Celsius, millimetres and kilometres per hour instead of silently relying on defaults. timezone=auto aligns daily dates with the chosen location. Parsing validates required fields, aligned array lengths, expected units, finite values and sensible temperature ranges. Weather descriptions follow the documented WMO mapping. Unknown codes stay visibly unknown rather than receiving invented meanings [W1].

Temperature and precipitation use separate chart axes because their units are incompatible. The shaded range means daily minimum to maximum, not a statistical confidence interval. The summary concerns only returned dates and does not make seasonal climate claims. MET provides instantaneous UTC temperatures. The notebook converts them to local dates and checks whether available samples fall inside corresponding Open-Meteo daily ranges. Sparse point samples are not true daily extrema; agreement is not proof of accuracy because no observations are involved [W5].

### Licensing and real-product implications

Open-Meteo distributes API data under CC BY 4.0, requiring attribution, a licence link and appropriate disclosure of adaptations. Geocoding uses GeoNames data, so that source also requires acknowledgement. Open data licensing differs from permission to use hosted infrastructure. The free endpoint is intended for non-commercial use and has published traffic limits. A commercial product needs an appropriate service arrangement or an independently assessed self-hosted deployment rather than assuming that openly licensed data permits unlimited free server access [W2, W3, W4].

MET generally offers its products under NLOD 2.0 and CC BY 4.0 unless otherwise specified. Commercial reuse remains subject to licensing and service terms. Its API requires an identifying User-Agent with actual contact details; generic identifiers may be blocked. This implementation truncates coordinates to four decimal places and makes a single compact MET forecast request per live run. Production use needs persistent caching, respect for cache headers and conditional requests such as If-Modified-Since. This teaching notebook does not implement that production cache and should not be turned into a high-traffic service unchanged [W5, W6, W7].

Forecast providers do not guarantee perfect accuracy or uninterrupted availability. A real agricultural advisory product would need monitoring, visible update times and uncertainty communication before users base expensive decisions on the output. Attribution should be beside the results, not hidden in a repository that end users may never see. The notebook therefore identifies providers next to transformed tables and charts, and separately announces synthetic offline provenance.

### Reliability, testing and reproducibility

Anticipated failures include empty location results, invalid coordinates, lost connections, short timeouts, server errors and malformed payload structures. Demonstrations deliberately simulate or construct those conditions; they are not claims that providers actually failed during development. The build environment cannot execute external HTTP. Consequently, genuine response times and live forecast observations remain to be checked locally. Recording that boundary prevents deterministic synthetic examples from being misrepresented as empirical network testing.

The requests wrapper retries connection errors, timeouts and HTTP 5xx responses. Two retries mean at most three attempts, with exponential waits of 0.5 and 1 second. Ordinary 4xx responses are not retried because repeating an invalid request normally cannot repair it. Final failure raises WeatherError with the attempt count and error category. The tiny-timeout example injects Timeout deterministically rather than hoping a particular network fails at exactly the desired instant. Transport tests independently check retry counts, status handling and backoff intervals.

Saved fixtures make parsing checks independent of the internet. Tests cover missing results, ambiguity, missing daily fields, mismatched arrays, wrong units, negative precipitation, nonfinite values, unknown codes and MET parsing. Fixed data and a seeded NumPy generator support reproducibility. Missing measurements currently raise explicit errors rather than silently affecting summaries. A production interface could display missing cells instead, but would need consistent plotting and aggregation rules so users are not misled by partial data.

### Privacy and operational boundaries

Geocoding discloses city queries to Open-Meteo. Forecast requests disclose coordinates to Open-Meteo and MET, while providers also see originating IP addresses and the contact email intentionally placed in User-Agent. HTTPS protects transport but does not conceal a query from its receiver. City-level queries are less precise than street addresses, yet repeated precise coordinates may reveal sensitive places or habits. The notebook does not request GPS permissions, and users should avoid entering unnecessary personal addresses.

Open-Meteo's policy describes technical logs that can include coordinates and a 90-day deletion period. This provider-specific statement is not a guarantee about every intermediary or future deployment [W3]. A real product should minimise precision, avoid unnecessary personal logs and explain third-party transfers. Keep the student's email in a local environment variable, not committed outputs. Before publishing, clear private outputs, check attribution and rerun both notebooks and all tests in a clean local environment.
