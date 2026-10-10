package com.insightedulab.backend_java.linkedin;

import java.util.List;

/**
 * Estructura JSON oficial de la API de Posts de LinkedIn (https://api.linkedin.com/rest/posts).
 */
public record LinkedinPostRequest(
        String author,
        String commentary,
        String visibility,
        Distribution distribution,
        String lifecycleState,
        boolean isReshareDisabledByAuthor
) {
    public record Distribution(
            String feedDistribution,
            List<String> targetEntities,
            List<String> thirdPartyDistributionChannels
    ) {}

    public static LinkedinPostRequest paraTexto(String authorUrn, String texto) {
        return new LinkedinPostRequest(
                authorUrn,
                texto,
                "PUBLIC",
                new Distribution("MAIN_FEED", List.of(), List.of()),
                "PUBLISHED",
                false
        );
    }
}
