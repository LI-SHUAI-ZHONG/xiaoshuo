export type paths = Record<string, never>;
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** CapabilityRequirement */
        CapabilityRequirement: {
            /** Code */
            code: string;
            /**
             * Configuration Path
             * @default null
             */
            configuration_path: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "configuration" | "permission" | "dependency" | "data";
            /** Message */
            message: string;
        };
        /**
         * CapabilityStatus
         * @description V2 adds independent axes; it does not replace legacy extension flags.
         */
        CapabilityStatus: {
            /** Capability */
            capability: string;
            /**
             * Configuration
             * @enum {string}
             */
            configuration: "missing" | "configured";
            /**
             * Data
             * @enum {string}
             */
            data: "empty" | "sufficient" | "insufficient";
            /** Enabled */
            enabled: boolean;
            /**
             * Evidence Refs
             * @default []
             */
            evidence_refs: string[];
            /**
             * Health
             * @enum {string}
             */
            health: "unknown" | "ready" | "degraded" | "unavailable";
            /**
             * Implementation
             * @enum {string}
             */
            implementation: "absent" | "port_only" | "implemented";
            /** Implementation Version */
            implementation_version: string | null;
            /**
             * Requirements
             * @default []
             */
            requirements: components["schemas"]["CapabilityRequirement"][];
            /**
             * Schema Version
             * @default 2
             * @constant
             */
            schema_version: 2;
            /**
             * Verification
             * @enum {string}
             */
            verification: "untested" | "verified" | "failed";
            /**
             * Verified At
             * @default null
             */
            verified_at: string | null;
        };
        /**
         * ContentRef
         * @description Immutable bytes owned by assets; hash is computed by the server.
         */
        ContentRef: {
            /**
             * Asset Id
             * Format: uuid
             */
            asset_id: string;
            /**
             * Asset Version Id
             * Format: uuid
             */
            asset_version_id: string;
            /** Byte Length */
            byte_length: number;
            /** Media Type */
            media_type: string;
            /** Sha256 */
            sha256: string;
        };
        /**
         * CursorPageRequest
         * @description Keyset pagination for new collections; legacy offset endpoints stay valid.
         */
        CursorPageRequest: {
            /**
             * Cursor
             * @default null
             */
            cursor: string | null;
            /**
             * Limit
             * @default 20
             */
            limit: number;
        };
        /**
         * DataOwner
         * @enum {string}
         */
        DataOwner: "identity" | "projects" | "assets" | "models" | "tools" | "workflows" | "agents" | "knowledge" | "memory" | "creative.novel" | "creative.world" | "creative.character" | "creative.creator" | "consistency" | "quality" | "feedback" | "evolution" | "ip" | "publishing" | "media" | "collaboration" | "ecosystem";
        /** EntityRevisionRef */
        EntityRevisionRef: {
            /** Branch Id */
            branch_id: string | null;
            /** Entity Type */
            entity_type: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            owner: components["schemas"]["DataOwner"];
            /**
             * Revision Id
             * Format: uuid
             */
            revision_id: string;
            /** Version */
            version: number;
        };
        /** Provenance */
        Provenance: {
            /**
             * Authority
             * @enum {string}
             */
            authority: "author_statement" | "accepted_fact" | "source_claim" | "candidate" | "inference";
            /**
             * Confidence
             * @default null
             */
            confidence: number | null;
            /**
             * Extraction Version
             * @default null
             */
            extraction_version: string | null;
            /** @default null */
            license_ref: components["schemas"]["EntityRevisionRef"] | null;
            /**
             * Model Profile Version
             * @default null
             */
            model_profile_version: string | null;
            /**
             * Prompt Version
             * @default null
             */
            prompt_version: string | null;
            /**
             * Run Id
             * @default null
             */
            run_id: string | null;
            /** Source Refs */
            source_refs: components["schemas"]["SourceRef"][];
            /**
             * Step Id
             * @default null
             */
            step_id: string | null;
        };
        /** RuntimePackageDependency */
        RuntimePackageDependency: {
            /** Manifest Sha256 */
            manifest_sha256: string;
            /** Package Id */
            package_id: string;
            /** Version */
            version: string;
        };
        /** RuntimePackageFile */
        RuntimePackageFile: {
            /** Byte Length */
            byte_length: number;
            /**
             * Kind
             * @enum {string}
             */
            kind: "prompt" | "workflow" | "rubric" | "schema" | "documentation" | "code" | "static_asset";
            /** Path */
            path: string;
            /** Sha256 */
            sha256: string;
        };
        /**
         * RuntimePackageManifest
         * @description Every runtime file is hashed; dependencies pin exact manifests, never latest.
         */
        RuntimePackageManifest: {
            /**
             * Dependencies
             * @default []
             */
            dependencies: components["schemas"]["RuntimePackageDependency"][];
            /** Entrypoints */
            entrypoints: {
                [key: string]: string;
            };
            /** Files */
            files: components["schemas"]["RuntimePackageFile"][];
            /**
             * Input Schema
             * @default null
             */
            input_schema: string | null;
            /** Minimum Contract Version */
            minimum_contract_version: string;
            /**
             * Output Schema
             * @default null
             */
            output_schema: string | null;
            owner: components["schemas"]["DataOwner"];
            /** Package Id */
            package_id: string;
            /**
             * Package Type
             * @enum {string}
             */
            package_type: "prompt" | "workflow" | "rubric" | "tool" | "agent" | "knowledge" | "content" | "ui-module" | "core-change";
            /**
             * Required Permissions
             * @default []
             */
            required_permissions: string[];
            /**
             * Schema Version
             * @default 1
             * @constant
             */
            schema_version: 1;
            /** Version */
            version: string;
        };
        /**
         * ScopeRef
         * @description Explicit anchor; the server must resolve grants before using this value.
         */
        ScopeRef: {
            /**
             * Anchor Id
             * Format: uuid
             */
            anchor_id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "workspace" | "project" | "universe" | "creator";
            /**
             * Workspace Id
             * Format: uuid
             */
            workspace_id: string;
        };
        /** SourceRef */
        SourceRef: {
            /** @default null */
            content: components["schemas"]["ContentRef"] | null;
            revision: components["schemas"]["EntityRevisionRef"];
            /** @default null */
            span: components["schemas"]["SourceSpan"] | null;
        };
        /**
         * SourceSpan
         * @description Offsets use Unicode code points, with an exclusive end, not UTF-8 bytes.
         */
        SourceSpan: {
            /**
             * Block Id
             * @default null
             */
            block_id: string | null;
            /** End */
            end: number;
            /**
             * Page
             * @default null
             */
            page: number | null;
            /** Start */
            start: number;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export type operations = Record<string, never>;
