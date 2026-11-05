# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# .github/rdvsp/agir.rb
#
# Essai CID ↔ RDV-Solidarités : simule ce qu'un USAGER ferait en ligne (données fictives).
#   bin/rails runner ../.github/rdvsp/agir.rb reserver <user_id> <motif_id> <lieu_id> <agent_id> <debut ISO8601>
#   bin/rails runner ../.github/rdvsp/agir.rb annuler <rdv_id>
# Affiche l'identifiant du RDV en JSON sur la dernière ligne.
require "json"

action = ARGV[0]
case action
when "reserver"
  user = User.find(ARGV[1])
  motif = Motif.find(ARGV[2])
  rdv = Rdv.new(organisation: motif.organisation, motif: motif, lieu: Lieu.find(ARGV[3]),
                agents: [Agent.find(ARGV[4])], starts_at: Time.zone.parse(ARGV[5]),
                duration_in_min: motif.default_duration_in_min, created_by: user, status: "unknown")
  rdv.participations.build(user: user, created_by: user)
  rdv.save!
  puts({ rdv_id: rdv.id }.to_json)
when "annuler"
  rdv = Rdv.find(ARGV[1])
  rdv.update!(status: "excused", cancelled_at: Time.zone.now)
  puts({ rdv_id: rdv.id }.to_json)
else
  abort "action inconnue : #{action}"
end
