# Disaster Management System – Volunteer & Assignment Engine

## Development Document (Layer 2 + Layer 3)

---

# 1. Purpose of This Module

This module manages the **rescue workforce and mission allocation** in the disaster management system.

It provides:

1. Registration and verification of responders
2. Classification of responders by capability and trust level
3. Automatic mission assignment to the best available responder
4. Mobile interface for responders to accept and complete missions
5. Support request system for additional help during rescue

This module ensures **SOS requests are matched with the most appropriate rescue resources quickly and safely**.

---

# 2. System Roles

The system supports four types of responders.

### Tier 1 – Government Rescue Teams

Examples:

* NDRF
* Fire & Rescue Department
* Police rescue units

Characteristics:

* Highest trust level
* Full rescue equipment
* Professionally trained
* Highest priority for assignments

Trust Score: **100**

---

### Tier 2 – NGO Rescue Teams

Examples:

* Red Cross
* Disaster response NGOs

Characteristics:

* Organized rescue teams
* Often have boats, medical teams, supplies

Trust Score: **80**

---

### Tier 3 – Verified Volunteers

Examples:

* Certified swimmers
* Medical volunteers
* Trained rescue helpers

Characteristics:

* Individual helpers
* Verified skills

Trust Score: **60**

---

### Tier 4 – Local Temporary Volunteers

Examples:

* Local fishermen
* Residents with boats
* Local helpers

Characteristics:

* Quick registration
* Minimal verification
* Useful for local navigation and assistance

Trust Score: **40**

These volunteers are assigned **lower-risk missions first**.

---

# 3. Volunteer / Responder Registration System

## Page

responders_register.html

Users can choose their role:

* Government Rescue Team
* NGO Team
* Certified Volunteer
* Local Volunteer

Different forms appear depending on selection.

---

# 4. Registration Forms

## Government Rescue Team Registration

Fields:

team_name
department
team_leader_name
team_leader_phone
team_size

equipment_available

* boat
* ambulance
* helicopter
* rescue gear

base_location
operating_radius_km

Verification:

government_id_document
department approval required

---

## NGO Registration

Fields:

organization_name
registration_number
contact_person
contact_phone

team_size

equipment_available

* boats
* ambulances
* medical staff
* rescue gear

operating_region

Verification:

NGO certificate upload
admin approval required

---

## Certified Volunteer Registration

Fields:

full_name
phone_number
age

skills

* swimming
* first aid
* boat driving
* medical training

equipment

* boat
* bike
* car

location
availability

Verification:

training certificate upload
manual approval by admin

---

## Local Volunteer Registration (Fast Registration)

Used during disaster emergencies.

Fields:

name
phone_number
village
current_location

skills

* boat driver
* swimmer
* helper

vehicle

* boat
* bike
* none

Verification:

SMS OTP verification only

Trust level automatically set to **Tier 4**

---

# 5. Responder Database Schema

Table: responders

Fields:

id
name
phone

type
(government / ngo / certified_volunteer / local_volunteer)

tier
trust_score

skills (array or JSON)

equipment (array or JSON)

vehicle_type

latitude
longitude

status

* available
* busy
* offline

verification_status

* pending
* approved
* rejected

availability

created_at

---

# 6. SOS Mission Assignment Engine

This module automatically selects the **best responder for each SOS request**.

Trigger:

When a new SOS is created.

API:

POST /api/sos/create

---

# 7. Mission Classification

The system first analyzes the SOS.

Example SOS:

people_count = 5
medical_emergency = true
elderly_present = true

System identifies mission type:

medical_rescue
flood_evacuation

---

# 8. Resource Requirement Detection

Based on the SOS type, the system determines required resources.

Example:

Case 1 – Flood rescue

Required resource:
boat team

Case 2 – Medical emergency

Required resources:
ambulance or medical volunteer

Case 3 – Flood + Medical

Required resources:
boat team + medical responder

---

# 9. Nearby Responder Search

System searches responders within a radius.

Search radius:

10 km (configurable)

Filters:

status = available
matching skill tags
matching equipment

---

# 10. Responder Scoring Algorithm

Each responder receives a score.

Score formula example:

score =
distance_score

* trust_score
* skill_match_score
* equipment_match_score
* availability_score

Example:

Responder A
distance = 2 km
trust_score = 100
equipment = boat

score = 210

Responder B
distance = 1 km
trust_score = 40
equipment = none

score = 80

Responder A is selected.

---

# 11. Multi-Team Assignment

Some missions require multiple responders.

Example:

SOS:
10 people trapped + medical emergency

Assigned resources:

boat team
medical volunteer

System creates a **mission group**.

---

# 12. Mission Database Schema

Table: missions

Fields:

id
sos_id

assigned_responder_ids (array)

mission_type

status

* assigned
* accepted
* en_route
* on_site
* rescue_completed
* mission_completed

assigned_at
completed_at

---

# 13. Responder Mobile Interface

Page:

responder_mobile.html

Login method:

phone_number + OTP

---

# 14. Volunteer Dashboard

After login responders see:

### Mission Alerts

New SOS near you

Displayed information:

distance
emergency_type
people_count
priority_level

Actions:

Accept Mission
Decline Mission

---

# 15. Navigation System

Map shows:

rescue location
nearby responders
shelters

Navigation uses map integration.

---

# 16. Mission Details Page

Displays:

people_count
emergency_type
special_notes

nearest_shelter_location

---

# 17. Mission Status Update

Responder updates progress.

Available buttons:

Start Journey
Reached Location
Rescue Completed
Mission Finished

These updates reflect in the command dashboard.

---

# 18. Nearby Rescue Team View

Responders can see nearby teams on the map.

Visible resources:

boats
ambulances
medical teams

Purpose:

team coordination during rescue operations.

---

# 19. Support Request System

If responders require additional help.

Example:

deep flood water
injured person
collapsed building

Responder can press:

REQUEST SUPPORT

Options:

Boat Team
Medical Team
Fire Team
Evacuation Vehicle

---

# 20. Support Request Flow

Volunteer requests support

API:

POST /api/support-request

System runs assignment engine again to find additional responders.

---

# 21. Area Condition Reports

Responders can submit environmental reports.

Fields:

location
water_level
road_blocked
fire_detected
building_damage

Saved in:

area_reports table

These reports update the command center map.

---

# 22. System Flow Summary

SOS created
→ Assignment engine triggered
→ Best responders selected
→ Mission created
→ Responder notified
→ Responder accepts mission
→ Navigation to SOS location
→ Rescue operation
→ Status updates sent
→ Mission completed

---

# 23. Key System Components

SOS Portal
Responder Registration System
Assignment Engine
Mission Management System
Responder Mobile Interface
Support Request System
Command Dashboard
Strategic Monitoring System

---

# End of Document



# Disaster Management System – Responder UI Design

## Volunteer / Rescue Team Interface Specification

This document defines the **user interface screens, components, and user flow** for the responder side of the disaster management system.

The UI is designed for:

* Government rescue teams
* NGO rescue teams
* Verified volunteers
* Local volunteers

The interface must be **mobile-first**, because responders mostly use phones during rescue operations.

---

# 1. Responder Registration UI

Page: `responders_register.html`

Purpose: allow different types of responders to register.

---

## Screen Layout

Top Section

Header Title:
"Register as Disaster Responder"

Short description:
"Join the rescue network to help people during disasters."

---

## Role Selection Cards

Four large cards displayed in a grid.

Card 1
Government Rescue Team

Card 2
NGO Rescue Team

Card 3
Certified Volunteer

Card 4
Local Volunteer

Each card includes:

icon
short description
register button

Example:

Government Rescue Team
Icon: shield
Description: Official disaster response team
Button: Register

---

# 2. Government Rescue Team Registration Form

After selecting Government Team.

Form Fields

Team Information

Team Name
Department
Team Leader Name
Leader Phone Number

Team Capacity

Team Size
Operating Radius (km)

Equipment Checklist

Boat
Ambulance
Helicopter
Rescue Gear
Medical Kit

Location

Base Location
Map picker for location

Verification

Upload government ID document

Submit Button

Register Team

---

# 3. NGO Registration Form

Organization Information

Organization Name
Registration Number
Contact Person
Phone Number

Team Information

Team Size
Operating Area

Equipment

Boats
Ambulances
Medical Staff
Rescue Equipment

Verification

Upload NGO certificate

Submit Button

Register Organization

---

# 4. Certified Volunteer Registration UI

Personal Information

Full Name
Phone Number
Age

Skills Selection

Checkbox list

Swimming
First Aid
Boat Driving
Medical Training
Fire Safety

Equipment

Boat
Bike
Car
None

Location

Current Location
Map picker

Verification

Upload training certificate

Submit Button

Register Volunteer

---

# 5. Local Volunteer Quick Registration

This form must be **very fast** because disasters require quick help.

Fields

Name
Phone Number

Village / Area

Skill Selection

Boat Driver
Swimmer
Helper

Vehicle

Boat
Bike
None

Location

Use GPS button

Button

Register as Local Volunteer

Verification

OTP verification

---

# 6. Responder Login UI

Page: `responder_login.html`

Login Method

Phone number

OTP authentication

Screen Layout

Title: Responder Login

Input field

Phone Number

Button

Send OTP

Next screen

OTP Input

Button

Verify

---

# 7. Responder Dashboard UI

Page: `responder_mobile.html`

This is the main interface for volunteers.

---

## Dashboard Layout

Top Section

Status Card

Your Status: Available / Busy

Toggle Button

Go Available
Go Offline

---

## New Mission Alert

Large alert card appears when new SOS nearby.

Card content

Emergency Type
Distance
People Count
Priority Level

Buttons

Accept Mission
Decline

---

## Map Section

Interactive map.

Markers displayed

SOS locations
Nearby responders
Shelters

Icons

Red marker → SOS
Blue marker → responder
Green marker → shelter

---

# 8. Mission Details Screen

When responder accepts mission.

Information shown

SOS Location
Distance
People Count
Emergency Type

Special notes

Example

Elderly present
Medical emergency

Navigation Button

Start Navigation

---

# 9. Mission Progress Panel

Responder updates status using buttons.

Buttons shown sequentially.

Start Journey

Reached Location

Rescue Completed

Mission Finished

Each button updates mission status.

---

# 10. Nearby Teams Screen

Responders can see other teams.

List view

Team Name
Type
Distance

Button

Contact Team

Map view also available.

---

# 11. Support Request UI

If volunteer needs help.

Button

Request Support

Popup options

Boat Team
Medical Team
Fire Team
Evacuation Vehicle

Optional message

Example

"Water level too high"

Submit Button

Send Support Request

---

# 12. Area Report Screen

Responders can submit condition reports.

Fields

Location (auto GPS)

Water Level

Low
Medium
High

Road Status

Open
Blocked

Building Damage

None
Partial
Severe

Button

Submit Report

---

# 13. Shelter Locator UI

Map shows nearest shelters.

Shelter card shows

Shelter Name
Distance
Capacity
Available Space

Button

Navigate to Shelter

---

# 14. Mission History Screen

Responder can see past missions.

List includes

Mission ID
Location
Date
Status

Status badge

Completed
Cancelled

---

# 15. Notification System

Responders receive alerts for:

New mission assignment
Support request from other teams
Emergency alerts

Notification banner appears on top.

---

# 16. UI Design Principles

Large buttons for quick actions

Minimum button height
60px

High contrast colors

Red → SOS
Blue → Responder
Green → Safe / Completed

Simple layouts

Minimal typing required

---

# 17. Mobile Optimization

Design optimized for:

low internet connectivity
small screens
quick interaction

Key features

offline cache support
large tap areas
minimal forms

---

# End of UI Specification
