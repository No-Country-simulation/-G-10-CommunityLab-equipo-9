package com.insightedulab.backend_java.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
@Builder
public class OciUploadResponseDto {
    private Long packageId;
    private String statusOci;
    private String rutaObjeto;
}