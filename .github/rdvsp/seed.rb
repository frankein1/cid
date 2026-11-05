# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# .github/rdvsp/seed.rb
#
# Essai CID ↔ RDV-Solidarités : données FICTIVES dans une copie éphémère de RDV-Solidarités
# (lancée par .github/workflows/essai-rdv-solidarites.yml, effacée à la fin).
#   cd mrs && bin/rails runner ../.github/rdvsp/seed.rb   → écrit $SEED_JSON
require "factory_bot"
require "faker"
require "json"
FactoryBot.find_definitions
include FactoryBot::Syntax::Methods

territory = create(:territory, name: "Bouches-du-Rhône (essai CID)", departement_number: "13")
orga = create(:organisation, territory: territory, name: "MDS TEST 01")
service = Service.find_by(name: Service::SERVICE_SOCIAL) || create(:service, :social)
TerritoryService.find_or_create_by!(territory: territory, service: service) if defined?(TerritoryService)
agent = create(:agent, email: "agent.essai@cid.test", first_name: "Agent", last_name: "Essai",
                       service: service, admin_role_in_organisations: [orga],
                       role_in_territories: [territory])   # administrateur de l'espace : déclare le webhook
AgentTerritorialAccessRight.find_or_create_by!(agent: agent, territory: territory)

# Pour l'essai de la synchronisation CID : une 2e MDS, et l'agente de CID qui y tient ses permanences
orga2 = create(:organisation, territory: territory, name: "MDS TEST 02")
AgentRole.create!(agent: agent, organisation: orga2, access_level: AgentRole::ACCESS_LEVEL_ADMIN)
agente = create(:agent, email: "ines.essai@cid.test", first_name: "Inès", last_name: "ESSAI", service: service,
                        basic_role_in_organisations: [orga2])

app = OauthApplication.create!(name: "CID (essai)", uid: "cid-essai", logo_base64: "",
                               redirect_uri: "http://localhost:8099/connecteurs/rdv-service-public/retour/",
                               scopes: "write")
jeton = Doorkeeper::AccessToken.create!(application: app, resource_owner_id: agent.id, scopes: "write",
                                        expires_in: 7200, use_refresh_token: true)

secret = app.plaintext_secret   # tiré par RDV-Solidarités et stocké haché : lisible seulement maintenant
puts "Diagnostic OAuth : application retrouvée par identifiant + secret = " \
     "#{Doorkeeper.config.application_model.by_uid_and_secret('cid-essai', secret).present?}, " \
     "confidentielle = #{app.confidential}, jeton rattaché = #{jeton.application_id == app.id}"

donnees = {
  territory_id: territory.id, organisation_id: orga.id, service_id: service.id,
  agent_id: agent.id, agent_email: agent.email,
  organisation2_id: orga2.id, agente_id: agente.id, agente_email: agente.email,
  jeton: jeton.plaintext_token, jeton_renouvellement: jeton.plaintext_refresh_token,
  client_id: app.uid, client_secret: secret,
}
File.write(ENV.fetch("SEED_JSON"), JSON.pretty_generate(donnees))
puts "Données fictives créées : organisation #{orga.id}, agent #{agent.id}"
