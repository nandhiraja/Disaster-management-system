# Disaster Response Platform

## Layer 1 – Affected People SOS Communication System

---

# 1. Purpose

This module allows **affected people during disasters** (floods, earthquakes, storms, etc.) to send an **SOS request to the rescue coordination system**.

The design must support **extreme disaster conditions**:

* No internet
* Weak network
* Low smartphone usage
* Panic situations
* Power outages
* Rural areas
* Non-technical users

The system must collect **minimal but critical rescue information** while keeping interaction extremely simple.

---

# 2. Design Principles

The system must follow these principles:

### 1. One-Action Emergency

Users must be able to trigger SOS with **one action**.

### 2. Multi-Channel Communication

SOS must work through multiple channels:

* Mobile App
* SMS
* Missed Call
* Volunteer Assisted Reporting

### 3. Minimal Input

Users cannot fill complex forms during emergencies.

### 4. Location Priority

Location must be captured automatically whenever possible.

### 5. Fail-Safe Design

If one channel fails, another must still work.

### 6. Offline First

App must store SOS locally and retry when network returns.

---

# 3. Communication Channels

The SOS system supports **four communication channels**.

## 3.1 Mobile App SOS

Primary method for smartphone users.

### Features

* One-tap SOS button
* Automatic GPS location capture
* Simple emergency type selection
* Retry sending if network fails

### SOS Screen UI

```
[ BIG RED SOS BUTTON ]

Emergency Type:
[ Medical ]
[ Trapped by Water ]
[ Elderly / Disabled ]
[ Children Present ]

People Count:
[ 1 ] [ 2 ] [ 3 ] [ 4+ ]

Send SOS
```

### Auto-Collected Data

The app automatically collects:

```
GPS Location
Phone Number
Timestamp
Battery Level
Network Strength
Device Type
```

### Behavior if Network Fails

If the network is unavailable:

```
Save SOS locally
Retry every 60 seconds
Switch to SMS fallback
```

---

# 4. SMS SOS

SMS must work for:

* basic phones
* low connectivity

### SMS Format

```
SOS <PeopleCount> <EmergencyType> <LocationCode>

Example:
SOS 3 MEDICAL
SOS 5 FLOOD
```

### Simplified Option

Users can also simply send:

```
SOS
```

The system will still record the request.

### Data Extraction

From SMS the system records:

```
phone_number
cell_tower_location
timestamp
message_content
```

If GPS is not available, approximate location is estimated using **cell tower data**.

---

# 5. Missed Call SOS

Many rural users cannot type messages.

A missed call system allows SOS reporting.

### Process

User calls a disaster helpline number.

Example:

```
1800-XXXX-SOS
```

Call automatically disconnects after a ring.

System records:

```
phone number
call timestamp
tower location
```

The backend creates an SOS request.

---

# 6. Volunteer Assisted SOS

In rural areas or areas without mobile signals, volunteers may encounter victims.

Volunteers can record SOS on behalf of victims.

Volunteer App Flow:

```
New SOS
↓
Capture Location
↓
People Count
↓
Emergency Type
↓
Submit
```

This method is important when:

* victims have no phones
* network is unavailable
* elderly cannot use technology

---

# 7. SOS Data Model

Every SOS request is stored in the system database.

### Table: sos_requests

Fields:

```
sos_id (UUID)

source_type
(app | sms | missed_call | volunteer)

phone_number

latitude
longitude
approx_location

people_count

emergency_type
medical
flood
trapped
unknown

status
pending
assigned
rescued
closed

created_time

priority_score
```

---

# 8. Priority Scoring

SOS requests must be prioritized automatically.

Example rules:

Medical emergency → High priority

```
+50 points
```

Children / elderly present

```
+20 points
```

Multiple people trapped

```
+10 points
```

Flood severe zone

```
+30 points
```

This score helps the rescue allocation system decide which SOS to handle first.

---

# 9. Location Estimation System

Location can come from several sources.

### GPS Location

Most accurate.

Collected from:

```
mobile app
volunteer app
```

### Cell Tower Location

Used when GPS unavailable.

Accuracy:

```
100m – 2km
```

### Map Area Approximation

If only phone number available, the system estimates using:

```
telecom tower area
recent user device location
```

---

# 10. SOS Status Lifecycle

Each SOS follows this lifecycle.

```
CREATED
↓
VERIFIED
↓
ASSIGNED
↓
RESCUE IN PROGRESS
↓
COMPLETED
```

---

# 11. Backend API

### Create SOS

```
POST /api/sos/create
```

Request:

```
{
  source_type: "app",
  latitude: 12.912,
  longitude: 77.222,
  people_count: 3,
  emergency_type: "medical"
}
```

---

### Fetch Nearby SOS

Used by rescue teams.

```
GET /api/sos/nearby
```

Parameters:

```
lat
lon
radius
```

---

### Update SOS Status

```
POST /api/sos/update-status
```

---

# 12. Offline Handling

The mobile app must support **offline SOS storage**.

Flow:

```
User presses SOS
↓
Data saved locally
↓
Network unavailable
↓
Retry send every 60 seconds
↓
Auto send when network returns
```

---

# 13. Security

Basic security protections:

* Rate limit fake SOS requests
* OTP verification for repeated reports
* duplicate SOS detection

Duplicate detection example:

```
same phone
same location
within 10 minutes
```

---

# 14. Integration with Other Layers

This layer feeds data to:

### Layer 2

Volunteer / Rescue allocation system.

### Layer 3

Disaster command center dashboard.

---

# 15. Prototype Scope

Prototype version should implement:

* Mobile App SOS
* SMS SOS
* Missed Call SOS
* Volunteer SOS reporting
* Basic backend API
* Database storage
* Map location capture

Advanced features (future):

* AI flood prediction
* satellite integration
* drone reconnaissance
* automated rescue planning

---

# End of Layer 1 Development Document
