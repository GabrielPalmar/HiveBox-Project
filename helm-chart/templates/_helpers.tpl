{{/* Pod-level securityContext */}}
{{- define "common.podSecurityContext" -}}
{{- with .Values.podSecurityContext }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/* Container-level securityContext */}}
{{- define "common.containerSecurityContext" -}}
{{- with .Values.containerSecurityContext }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/* Resources per workload (hivebox, redis, minio, cronjob) */}}
{{- define "common.resources" -}}
{{- $vals := .Values -}}
{{- $name := .name -}}
{{- with (index $vals.resources $name) }}
{{ toYaml . }}
{{- end }}
{{- end }}
