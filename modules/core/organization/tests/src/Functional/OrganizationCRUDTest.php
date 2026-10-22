<?php

declare(strict_types=1);

namespace Drupal\Tests\organization\Functional;

use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\organization\Entity\Organization;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\RunTestsInSeparateProcesses;

/**
 * Tests the organization CRUD.
 */
#[Group('farm')]
#[RunTestsInSeparateProcesses]
class OrganizationCRUDTest extends OrganizationTestBase {

  use StringTranslationTrait;

  /**
   * Fields are displayed correctly.
   */
  public function testFieldsVisibility() {
    $this->drupalGet('organization/add/default');
    $assert_session = $this->assertSession();
    $assert_session->statusCodeEquals(200);
    $assert_session->fieldExists('name[0][value]');
    $assert_session->fieldExists('revision_log_message[0][value]');
    $assert_session->fieldExists('uid[0][target_id]');
    $assert_session->fieldExists('created[0][value][date]');
    $assert_session->fieldExists('created[0][value][time]');
  }

  /**
   * Create organization entity.
   */
  public function testCreateOrganization() {
    $assert_session = $this->assertSession();
    $name = $this->randomMachineName();
    $edit = [
      'name[0][value]' => $name,
    ];

    $this->drupalGet('organization/add/default');
    $this->submitForm($edit, 'Save');

    $result = \Drupal::entityTypeManager()
      ->getStorage('organization')
      ->getQuery()
      ->accessCheck(TRUE)
      ->range(0, 1)
      ->execute();
    $organization_id = reset($result);
    $organization = Organization::load($organization_id);
    $this->assertEquals($organization->get('name')->value, $name, 'organization has been saved.');

    $assert_session->pageTextContains("Saved organization: $name");
    $assert_session->pageTextContains($name);

    // Test that organization names must be unique.
    $this->drupalGet('organization/add/default');
    $edit = [
      'name[0][value]' => $organization->get('name')->value,
    ];
    $this->submitForm($edit, 'Save');
    $assert_session->pageTextNotContains("Saved organization: $name");
    $assert_session->pageTextContains("A organization with Name $name already exists.");
  }

  /**
   * Display organization entity.
   */
  public function testViewOrganization() {
    $edit = [
      'name' => $this->randomMachineName(),
      'created' => \Drupal::time()->getRequestTime(),
    ];
    $organization = $this->createOrganizationEntity($edit);
    $organization->save();

    $this->drupalGet($organization->toUrl('canonical'));
    $this->assertSession()->statusCodeEquals(200);

    $this->assertSession()->pageTextContains($edit['name']);
    $this->assertSession()->responseContains(\Drupal::service('date.formatter')->format(\Drupal::time()->getRequestTime()));
  }

  /**
   * Edit organization entity.
   */
  public function testEditOrganization() {
    $organization = $this->createOrganizationEntity();
    $organization->save();

    $edit = [
      'name[0][value]' => $this->randomMachineName(),
    ];
    $this->drupalGet($organization->toUrl('edit-form'));
    $this->submitForm($edit, 'Save');
    $this->assertSession()->pageTextContains($edit['name[0][value]']);
  }

  /**
   * Delete organization entity.
   */
  public function testDeleteOrganization() {
    $organization = $this->createOrganizationEntity();
    $organization->save();

    $label = $organization->getName();
    $organization_id = $organization->id();

    $this->drupalGet($organization->toUrl('delete-form'));
    $this->submitForm([], 'Delete');
    $this->assertSession()->responseContains($this->t('The @entity-type %label has been deleted.', [
      '@entity-type' => $organization->getEntityType()->getSingularLabel(),
      '%label' => $label,
    ]));
    $this->assertNull(Organization::load($organization_id));
  }

}
